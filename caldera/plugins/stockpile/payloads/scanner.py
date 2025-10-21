import argparse
import socket

DEFAULT_TIMEOUT = 0.5
SUCCESS = 0


def check_port(*host_port, timeout=DEFAULT_TIMEOUT):
    sock = socket.socket()
    sock.settimeout(timeout)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    connected = sock.connect_ex(host_port) is SUCCESS
    sock.close()
    return connected


parser = argparse.ArgumentParser('homemade port scanner')
parser.add_argument('-i', '--ip', required=True, default='127.0.0.1', help='Send me an IP to scan popular ports')
args = parser.parse_args()

for port in [21, 22, 53, 80, 443, 1023, 3000, 3283, 3306, 4444, 5000, 5432, 5601, 6379, 7474, 8000, 8080, 8090, 8172,
             8888, 9092, 9200, 27017]:
    if check_port(args.ip, port):
        print('%s:%s' % (args.ip, port))
