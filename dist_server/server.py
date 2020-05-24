import os
import time
import json
import pexpect
from tqdm import trange, tqdm
from threading import Thread, Lock, Timer
from concurrent.futures import ThreadPoolExecutor

from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport
from thrift.transport import TSocket
from thrift.server import TServer

import dist_server.rpc.pyrpc.pyrpc as server
import dist_server.rpc.constants as constants
from dist_server import __version__

from dist_server.util import start_server, stop_server


class Handler(object):
    def __init__(self, config, debug):
        self.config = json.load(open(config))
        self.debug = debug
        if self.debug:
            print('Debug log enabled.')
        self._lock = Lock()
        self._reset()
        self.cmd_cfg = self.config['cmd']
        self.instances = self.cmd_cfg['instances']
        self.num = len(self.instances)
        self.pool = ThreadPoolExecutor(self.num)
        self.work_dir = self.cmd_cfg['work_dir']
        self.pattern = self.cmd_cfg['pattern']
        self.timeout = self.cmd_cfg['timeout']
        self.expect_pattern = self.cmd_cfg['expect_pattern']
        self.error_pattern = self.cmd_cfg['error_pattern']
        self.srv_cfg = self.config['service']

    def _reset(self):
        self.avail_ports = []
        self.sessions = {}
        self.conns = {}

    def ping(self):
        return

    def version(self):
        return __version__

    def start_server(self):
        self._lock.acquire()
        futures = []
        for i in range(self.num):
            instance = self.instances[i]
            port = instance['port']
            cmd = self.pattern.format(*instance['args'])
            f = self.pool.submit(start_server, cmd, port, self.work_dir,
                                 self.expect_pattern, self.error_pattern,
                                 self.timeout, self.debug)
            futures.append(f)
        for f in tqdm(futures, dynamic_ncols=True):
            port, result, p = f.result()
            if result:
                self.sessions[port] = p
                self.avail_ports.append(port)
                self.conns[port] = 0
            else:
                print('Port {} fail to start.'.format(port))
        self._lock.release()
        self.create_timer()

    def stop_server(self):
        self.t.cancel()
        self._lock.acquire()
        for port in tqdm(self.avail_ports):
            stop_server(self.sessions[port], port, self.debug)
        self._lock.release()
        self._reset()

    def acquire_port(self):
        if self.srv_cfg['singleton']:
            while len([v for v in self.conns.values() if v == 0]) == 0:
                time.sleep(0.1)
        self._lock.acquire()
        port = sorted(self.conns.items(), key=lambda x: x[1])[0][0]
        self.conns[port] += 1
        self._lock.release()
        return port

    def release_port(self, port):
        self._lock.acquire()
        if self.conns[port] > 0:
            self.conns[port] -= 1
        self._lock.release()

    def reset(self):
        self._lock.acquire()
        for k in self.conns:
            self.conns[k] = 0
        self._lock.release()

    def create_timer(self):
        self.t = Timer(0.1, self.check_output)
        self.t.start()

    def check_output(self):
        flag = True
        for p in self.sessions.values():
            try:
                p.read_nonblocking(size=int(1e10), timeout=0.1)
            except pexpect.exceptions.TIMEOUT:
                pass
            except Exception:
                flag = False
                pass
        if flag:
            self.create_timer()


class ServerThread(Thread):
    def __init__(self, port, config, debug):
        super(ServerThread, self).__init__()
        self.daemon = True
        self.host = '0.0.0.0'
        self.port = port
        self.config = config
        self.debug = debug
        self.handler = None

    def run(self):
        self.handler = Handler(self.config, self.debug)
        print('Starting servers...')
        self.handler.start_server()
        processor = server.Processor(self.handler)
        transport = TSocket.TServerSocket(self.host, self.port)
        tfactory = TTransport.TBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolFactory()

        rpc_server = TServer.TThreadPoolServer(processor, transport, tfactory,
                                               pfactory)
        rpc_server.setNumThreads(100)

        print('Starting the RPC at', self.host, ':', constants.PORT)
        rpc_server.serve()


class Server(object):
    def __init__(self, port, config, debug):
        self.port = port
        self.config = config
        self.debug = debug

    def start(self):
        import time
        self.server_thread = ServerThread(self.port, self.config, self.debug)
        self.server_thread.start()
        time.sleep(0.5)
        help_str = 'Available Commands:\n' \
                   '\texit or e: Exit\n' \
                   '\tquery or q: Query available ports\n' \
                   '\tlist or l: List all connections\n' \
                   '\treset or r: Reset used ports\n' \
                   '\thelp or h: This message\n'
        try:
            while True:
                cmd = input()
                if cmd == 'exit' or cmd == 'e':
                    break
                elif cmd == 'query' or cmd == 'q':
                    print(self.server_thread.handler.avail_ports)
                elif cmd == 'list' or cmd == 'l':
                    print(self.server_thread.handler.conns)
                elif cmd == 'reset' or cmd == 'r':
                    self.server_thread.handler.reset()
                    print('Reset')
                elif cmd == 'help' or cmd == 'h':
                    print(help_str)
                else:
                    print('Unknown command, type help for command.')
        except:
            import traceback
            traceback.print_exc()
        finally:
            print('Stopping servers...')
            self.server_thread.handler.stop_server()
            print('Stopped')
            os._exit(0)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description='Python Distribute Server')
    parser.add_argument('-p', '--port', type=int, default=constants.PORT,
                        help='Host Port')
    parser.add_argument('-c', '--config', type=str, required=True,
                        help='Config file')
    parser.add_argument('-d', '--debug', type=bool, default=False,
                        help='Enable debug mode')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    Server(args.port, args.config, args.debug).start()
