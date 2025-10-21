# Troubleshooting

## Installing MITRE Caldera

If `donut-shellcode` installation fails, ensure that prerequisite packages are installed
  - Amazon Linux 2:
    - `gcc`
    - `python3-devel`

## Starting Caldera

1. Ensure that Caldera has been cloned recursively. Plugins are stored in submodules and must be cloned along with the core code.
1. Check that Python 3.8+ is installed and being used. 
1. Confirm that all `pip` requirements have been fulfilled.
1. Run the Caldera server with the `--log DEBUG` parameter to see if there is additional output.
1. Consider removing the `conf/local.yml` and letting Caldera recreate the file when the server runs again.

### Module Not Found Error

If you get an error like `ModuleNotFoundError: No module named 'plugins.manx.app'` when starting Caldera:
1. Check to see if the `plugins/manx` folder is empty
   1. Ensure that Caldera has been cloned recursively. Plugins are stored in submodules and must be cloned along with the core code.
   1. Alternatively, from the plugins folder, you can run `git clone https://github.com/mitre/manx.git` to grab only the manx repo.
1. Check your `conf/local.yml` to make sure manx is enabled


## Stopping Caldera

Caldera has a backup, cleanup, and save procedure that runs when the key combination `CTRL+C` is pressed. This is the recommended method to ensure proper shutdown of the server. If the Python process executing Caldera is halted abruptly (for example SIGKILL) it can cause information from plugins to get lost or configuration settings to not reflect on a server restart.

## Agent Deployment

### Downloading the agent

1. Check the server logs for the incoming connection. If there is no connection:
   1. Check for any output from the agent download command which could give additional information.
   1. Make sure the agent is attempting to connect to the correct address (not `0.0.0.0` and likely not `127.0.0.1`).
   1. Check that the listen interface is the same interface the agent is attempting to connect to.
   1. Check that the firewall is open, allowing network connections, between the remote computer running the agent and the server itself.
1. Ensure Go is properly installed (required to dynamically-compile Sandcat):
   1. Make sure the Go environment variables are properly set. Ensure the PATH variable includes the Go binaries by adding this to the `/etc/profile` or similar file: 
      ```
      export PATH=$PATH:/usr/local/go/bin
      ```
   2. If there are issues with a specific package, run something like the following:
      ```
      go get -u github.com/google/go-github/github
      go get -u golang.org/x/oauth2
      ```

### Running the agent

1. Run the agent with the `-v` flag and without the `-WindowStyle hidden` parameter to view output.
1. Consider removing bootstrap abilities so the console isn't cleared.

## Operations

### No operation output

1. Ensure that at least one agent is running before running the operation.
   1. Check that the agent is running either on the server or in the agent-specific settings under last checked in time.
   1. Alternatively, clear out the running agent list using the red X's. Wait for active agents to check in and repopulate the table.
1. Ensure that an adversary is selected before running the operation.
1. Check each ability on the adversary profile.
   1. Abilities show an icon for which operating system they run on. Match this up with the operating systems of the running agents.
   1. Abilities have specific executors in the details. Match this up with the executors of the running agents (found under the agent-specific settings).
   1. Look at each ability command. If there is a fact variable inside - shown by #{} syntax - the ability will need to be "unlocked" by another ability, in a prior step, before it can run. 

## Opening Files

1. Files are encrypted by default and can be decrypted with the following utility: <https://github.com/mitre/caldera/blob/master/app/utility/file_decryptor.py> 
