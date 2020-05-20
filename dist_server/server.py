from threading import Thread, Lock

from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport
from thrift.transport import TSocket
from thrift.server import TServer

import dist_server.rpc.pyrpc.pyrpc as server
import dist_server.rpc.constants as constants
from dist_server import __version__

import copy
import time
import json
from tqdm import trange
from dist_server.util import start_server, stop_server


class Handler(object):
    def __init__(self, config, debug):
        self.config = json.load(open(config))
        self.debug = debug
        self._lock = Lock()
        self.avail_ports = []
        self.conns = {}
        self.cmd_cfg = self.config['cmd']
        self.instances = self.cmd_cfg['instances']
        self.num = len(self.instances)
        self.work_dir = self.cmd_cfg['work_dir']
        self.pattern = self.cmd_cfg['pattern']
        self.timeout = self.cmd_cfg['timeout']
        self.srv_cfg = self.config['service']

    def ping(self):
        return

    def version(self):
        return __version__

    def start_server(self):
        self._lock.acquire()
        for i in trange(self.num):
            instance = self.instances[i]
            port = instance['port']
            cmd = self.pattern.format(*instance['args'])
            result = start_server(cmd, port, self.work_dir,
                                  self.timeout, self.debug)
            if result:
                self.avail_ports.append(port)
                self.conns[port] = 0
            else:
                print('Port {} fail to start.'.format(instance['port']))
        self._lock.release()

    def stop_server(self):
        self._lock.acquire()
        for port in self.avail_ports:
            stop_server(port, self.debug)
        self._lock.release()

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
        while True:
            cmd = input()
            if cmd == 'exit' or cmd == 'e':
                break


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description='Python RPC server')
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
