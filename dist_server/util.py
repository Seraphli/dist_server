def get_path(name='log', abspath=None, relative_path=None,
             _file=None, parent=False):
    """Create path if path don't exist
    Args:
        name: folder name
        abspath: absolute path to be prefix
        relative_path: relative path that can be convert into absolute path
        _file: use directory based on _file
        parent: whether the path is in the parent folder
    Returns: Path of the folder
    """
    import os
    if abspath:
        directory = os.path.abspath(os.path.join(abspath, name))
    elif relative_path:
        directory = os.path.abspath(os.path.join(
            os.path.abspath(relative_path), name))
    else:
        if _file:
            if parent:
                directory = os.path.abspath(
                    os.path.join(os.path.dirname(_file), os.pardir, name))
            else:
                directory = os.path.abspath(
                    os.path.join(os.path.dirname(_file), name))
        else:
            if parent:
                directory = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), os.pardir, name))
            else:
                directory = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), name))
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


import pexpect
import sys
import time


def port_check(address, port):
    import socket
    s = socket.socket()
    try:
        s.connect((address, port))
        return True
    except socket.error as e:
        return False
    finally:
        s.close()


def start_server(cmd, port, work_dir, timeout, debug=False, max_try=5):
    if debug:
        _logfile = sys.stdout
    else:
        _logfile = None
    retry = 0
    while retry < max_try:
        p = pexpect.spawn('bash', cwd=work_dir, encoding='utf-8')
        p.logfile_read = _logfile
        p.expect(['#', '$', pexpect.TIMEOUT], timeout=1)
        p.read_nonblocking(size=int(1e10), timeout=1)
        p.sendline(cmd)
        time.sleep(timeout)
        p.read_nonblocking(size=int(1e10), timeout=1)
        if not port_check('127.0.0.1', port):
            p.close()
            stop_server(port, debug)
            retry += 1
            continue
        return True, p
    return False, None


def stop_server(proc, port, debug=False):
    if debug:
        _logfile = sys.stdout
    else:
        _logfile = None
    proc.close()
    time.sleep(0.5)
    if port_check('127.0.0.1', port):
        p = pexpect.spawn('bash', encoding='utf-8')
        p.logfile_read = _logfile
        p.expect(['#', '$', pexpect.TIMEOUT], timeout=1)
        p.read_nonblocking(size=int(1e10), timeout=1)
        p.sendline(f'kill -9 $(lsof -t -i:{port})')
        p.expect(['#', '$', pexpect.TIMEOUT], timeout=1)
        p.read_nonblocking(size=int(1e10), timeout=1)
        p.close()
