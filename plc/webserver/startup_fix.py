import subprocess
import openplc
import time

compile_path = '/workdir/webserver/scripts/compile_program.sh'
active_program = subprocess.check_output(['cat','/workdir/webserver/active_program']).decode().strip()

output = subprocess.check_output([compile_path,active_program])

rt = openplc.runtime()
rt.stop_runtime()
time.sleep(3)

rt.start_runtime()
