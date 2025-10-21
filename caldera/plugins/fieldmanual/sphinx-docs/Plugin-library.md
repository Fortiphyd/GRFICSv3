# Plugin library

Here you'll get a run-down of all open-source plugins, all of which can be found in the plugins/ directory as separate 
GIT repositories. 

To enable a plugin, add it to the `default.yml` file in the `conf/` directory. Make sure your server is stopped when editing the `default.yml` file.

Plugins can also be enabled through the GUI. Go to *Advanced -> Configuration* and then click on the 'enable' button for the plugin you would like to enable.

## Sandcat

The Sandcat plugin contains Caldera's default agent, which is written in GoLang for
cross-platform compatibility. 

The agent will periodically beacon to the C2 server to receive instructions, execute instructions
on the target host, and then send results back to the C2 server.
The agent also supports payload downloads, file uploads, and a variety of execution and C2 communication options.
For more details, see the [Sandcat plugin documentation](plugins/sandcat/Sandcat-Details.md)

### Deploy 

To deploy Sandcat, use one of the built-in delivery commands which allows you to run the agent on any operating system. 
Each of these commands downloads the compiled Sandcat executable from Caldera and runs it immediately. Find
the commands on the Sandcat plugin tab.

Once the agent is running, it should show log messages when it beacons into Caldera.

> If you have GoLang installed on the Caldera server, each time you run one of the delivery commands above, 
the agent will re-compile itself dynamically and it will change it's source code so it gets a different file 
hash (MD5) and a random name that blends into the operating system. This will help bypass file-based signature detections.

### Options

When deploying a Sandcat agent, there are optional parameters you can use when you start the executable:

* **Server**: This is the location of Caldera. The agent must have connectivity to this host/port. 
* **Group**: This is the group name that you would like the agent to join when it starts. The group does not have to exist. A default group of my_group will be used if none is passed in.
* **v**: Use `-v` to see verbose output from sandcat.  Otherwise, sandcat will run silently.

### Extensions
In order to keep the agent code lightweight, the default Sandcat agent binary ships with limited basic functionality.
Users can dynamically compile additional features, referred to as "gocat extensions". Each extension adds to the 
existing `gocat` module code to provide functionality such as peer-to-peer proxy implementations, additional
executors, and additional C2 contact protocols. 

To request particular gocat extensions, users can 
include the `gocat-extensions` HTTP header when asking the C2 to compile an agent. The header value
must be a comma-separated list of requested extensions. The server will include the extensions in
the binary if they exist and if their dependencies are met (i.e. if extension A requires a particular
Golang module that is not installed on the server, then extension A will not be included).

Below is an example powershell snippet to request the C2 server to include the `proxy_http` and `shells` 
extensions:
```
$url="http://192.168.137.1:8888/file/download"; # change server IP/port as needed
$wc=New-Object System.Net.WebClient;
$wc.Headers.add("platform","windows"); # specifying Windows build
$wc.Headers.add("file","sandcat.go"); # requesting sandcat binary
$wc.Headers.add("gocat-extensions","proxy_http,shells"); # requesting the extensions
$output="C:\Users\Public\sandcat.exe"; # specify destination filename
$wc.DownloadFile($url,$output); # download
```

The following features are included in the stock agent:
- `HTTP` C2 contact protocol
- `psh` PowerShell executor (Windows)
- `cmd` cmd.exe executor (Windows)
- `sh` shell executor (Linux/Mac)
- `proc` executor to directly spawn processes from executables without needing to invoke a shell (Windows/Linux/Mac)

Additional functionality can be found in the following gocat extensions:
- `gist` extension provides the Github gist C2 contact protocol.
- `shells` extension provides the `osascript` (Mac Osascript) and `pwsh` (Windows powershell core) executors.
- `shellcode` extension provides the shellcode executors.
- `proxy_http` extension provides the `HTTP` peer-to-peer proxy receiver.
- `proxy_smb_pipe` extension provides the `SmbPipe` peer-to-peer proxy client and receiver for Windows (peer-to-peer
communication via SMB named pipes).
- `donut` extension provides the Donut functionality to execute various assemblies in memory. 
See https://github.com/TheWover/donut for additional information.
- `shared` extension provides the C sharing functionality for Sandcat.

#### Exit Codes

Exit codes returned from Sandcat vary across executors. Typical shell executors will return the exit code provided by the shell. Certain executor extensions will return values hard-coded in Sandcat.

Sandcat includes general exit codes which may be utilized by executors, overriden by executors, or used in error cases. The following values describe general Sandcat exit codes:
- `-1`: Error (e.g., cannot decode command, payload not available)
- `0`: Success

The following values describe exit codes utilized by specific executors:
- `shells`: Returns the exit code provided by the OS/shell.
- `shellcode`: Utilizes the general Sandcat exit codes.
- `native` and `native_aws`:
    - `0`: Success
    - `1`: Process error (e.g., error while executing code)
    - `2`: Input error (e.g., invalid parameters)
- `donut`: Returns the exit code provided by the OS/shell.

#### Customizing Default Options & Execution Without CLI Options

It's possible to customize the default values of these options when pulling Sandcat from the Caldera server.  
This is useful if you want to hide the parameters from the process tree. You can do this by passing the values
in as headers instead of as parameters.

For example, the following will download a linux executable that will use `http://10.0.0.2:8888` as the server address 
instead of `http://localhost:8888`.

```
curl -sk -X POST -H 'file:sandcat.go' -H 'platform:linux' -H 'server:http://10.0.0.2:8888' http://localhost:8888/file/download > sandcat.sh
```
## Caldera for OT

The Caldera for OT plugins extend Caldera by providing support for common industrial protocols. Each plugin contains a collection of abilities unique to an operational technology (OT) protocol.
To install the plugins and learn more about which protocols are currently supported, visit: [https://github.com/mitre/caldera-ot](https://github.com/mitre/caldera-ot).

## Mock 

The Mock plugin adds a set of simulated agents to Caldera and allows you to run complete operations without hooking any other computers up to your server. 

These agents are created inside the `conf/agents.yml` file. They can be edited and you can create as many as you'd like. A sample agent looks like:
```
- paw: 1234
  username: darthvader
  host: deathstar
  group: simulation
  platform: windows
  location: C:\Users\Public
  enabled: True
  privilege: User
  c2: HTTP
  exe_name: sandcat.exe
  executors:
    - pwsh
    - psh
```

After you load the mock plugin and restart Caldera, all simulated agents will appear as normal agents in the Chain plugin GUI and can be used in any operation.

## Manx

The terminal plugin adds reverse-shell capability to Caldera, along with a TCP-based agent called Manx.

When this plugin is loaded, you'll get access to a new GUI page which allows you to drop reverse-shells on target hosts 
and interact manually with the hosts. 

You can use the terminal emulator on the Terminal GUI page to interact with your sessions. 

## Stockpile

The stockpile plugin adds a few components to Caldera:

* Abilities
* Adversaries
* Planner
* Facts

These components are all loaded through the `plugins/stockpile/data/*` directory.

## Response

The response plugin is an autonomous incident response plugin, which can fight back against adversaries
on a compromised host.

Similar to the stockpile plugin, it contains adversaries, abilities, and facts intended for incident response. These components are all loaded through the `plugins/response/data/*` directory.

## Compass

Create visualizations to explore TTPs. Follow the steps below to create your own visualization:

1. Click 'Generate Layer'
1. Click '+' to open a new tab in the navigator
1. Select 'Open Existing Layer'
1. Select 'Upload from local' and upload the generated layer file

Compass leverages ATT&CK Navigator, for more information see: [https://github.com/mitre-attack/attack-navigator](https://github.com/mitre-attack/attack-navigator)

## Caltack

The caltack plugin adds the public MITRE ATT&CK website to Caldera. This is useful for deployments of Caldera where an operator cannot access the Internet to reference the MITRE ATT&CK matrix.

After loading this plugin and restarting, the ATT&CK website is available from the Caldera home page. Not all parts of the ATT&CK website will be available - but we aim to keep those pertaining to tactics and techniques accessible.

## SSL

The SSL plugin adds HTTPS to Caldera. 
> This plugin only works if Caldera is running on a Linux or MacOS machine. It requires HaProxy (>= 1.8) to be installed prior to using it.

When this plugin has been loaded, Caldera will start the HAProxy service on the machine and serve Caldera on all interfaces on port 8443, in addition to the normal http://[YOUR_IP]:8888 (based on the value of the `host` value in the Caldera settings).

Plugins and agents will not automatically update to the service at https://[YOUR_IP]:8443. All agents will need to be redeployed using the HTTPS address to use the secure protocol. The address will not automatically populate in the agent deployment menu. If a self-signed certificate is used, deploying agents may require additional commands to disable SSL certificate checks (such as using the `--insecure` flag to bypass SSL certificate checks in the initial `curl` request when downloading the new agents).

**Warning:** This plugin uses a default self-signed ssl certificate and key which should be replaced. In order to use this plugin securely, you need to generate your own certificate. The directions below show how to generate a new self-signed certificate. If you are unable to connect to Caldera using the self-signed certificate, verify that your system trusts the certificate.

### Setup Instructions

*Note: OpenSSL must be installed on your system to generate a new self-signed certificate*

1. install haproxy >= 1.8 using `brew install haproxy` (MacOS) or `sudo apt-get install haproxy` (Linux).
2. In the root Caldera directory, navigate to `plugins/ssl`.
3. Place a PEM file containing SSL public and private keys in `conf/certificate.pem`. Follow the instructions below to generate a new self-signed certificate:
   - In a terminal, paste the command `openssl req -x509 -newkey rsa:4096  -out conf/certificate.pem -keyout conf/certificate.pem -nodes` and press enter.
   - This will prompt you for identifying details. Enter your country code when prompted. You may leave the rest blank by pressing enter.
4. Copy the file `haproxy.conf` from the `templates` directory to the `conf` directory.
5. Open the file `conf/haproxy.conf` in a text editor.
6. On the line `bind *:8443 ssl crt plugins/ssl/conf/insecure_certificate.pem`, replace `insecure_certificate.pem` with `certificate.pem`.
7. On the line `server caldera_main 127.0.0.1:8888 cookie caldera_main`, replace `127.0.0.1:8888` with the host and port defined in Caldera's `conf/local.yml` file. This should not be required if Caldera's configuration has not been changed.
8. Save and close the file. Congratulations! You can now use Caldera securely by accessing the UI https://[YOUR_IP]:8443 and redeploying agents using the HTTPS service.


## Atomic

The Atomic plugin imports all Red Canary Atomic tests from their open-source GitHub repository.

## GameBoard

The GameBoard plugin allows you to monitor both red-and-blue team operations. The game tracks points for both sides
and determines which one is "winning". The scoring seeks to quantify the amount of true/false positives/negatives
produced by the blue team. The blue team is rewarded points when they are able to catch the red team's actions, and the
red team is rewarded when the blue team is not able to correctly do so. Additionally, abilities are rewarded different amounts of
points depending on the tactic they fulfill.

To begin a gameboard exercise, first log in as blue user and deploy an agent. The 'Auto-Collect' operation will execute automatically. Alternatively, you can begin a different operation with the blue agent if you desire. Log in as red user and begin another operation. Open up the gameboard plugin from the GUI and select these new respective red and blue operations to monitor points for each operation. 

## Human

The Human plugin allows you to build "Humans" that will perform user actions on a target system as a means to obfuscate 
red actions by Caldera. Each human is built for a specific operating system and leverages the Chrome browser along with other native 
OS applications to perform a variety of tasks.  Additionally, these humans can have various aspects of their behavior "tuned"
to add randomization to the behaviors on the target system.

On the Caldera server, there are additional python packages required in order to use the Human plugin.
These python packages can be installed by navigating to the `plugins/human/` directory and running the command `pip3 install -r requirements.txt`

With the python package installed and the plugin enabled in the configuration file, the Human plugin is ready for use.
When opening the plugin within Caldera, there are a few actions that the human can perform.
Check the box for each action you would like the human to perform. 
Once the actions are selected, then "Generate" the human.

The generated human will show a deployment command for how to run it on a target machine.
Before deploying the human on a target machine, there are 3 requirements:

1. Install python3 on the target machine
2. Install the python package `virtualenv` on the target machine
3. Install Google Chrome on the target machine

Once the requirements above are met, then copy the human deployment command from the Caldera server and run it on the target machine.
The deployment command downloads a tar file from the Caldera server, un-archives it, and starts the human using python.
The human runs in a python virtual environment to ensure there are no package conflicts with pre-existing packages.

## Training

This plugin allows a user to gain a "User Certificate" which proves their ability to use Caldera. This is the first of several certificates planned in the future. The plugin takes you through a capture-the-flag style certification course, covering all parts Caldera.

## Access

This plugin allows you to task any agent with any ability from the database. It also allows you to conduct [Initial Access Attacks](Initial-Access-Attacks.md).

### Metasploit Integration

The Access plugin also allows for the easy creation of abilities for Metasploit exploits.

Prerequisites:

* An agent running on a host that has Metasploit installed and initialized (run it once to set up Metasploit's database)
* The `app.contact.http` option in Caldera's configuration includes `http://`
* A fact source that includes a `app.api_key.red` fact with a value equal to the `api_key_red` option in Caldera's configuration

Within the `build-capabilities` tactic there is an ability called `Load Metasploit Abilities`. Run this ability with an agent and fact source as described above, which will add a new ability for each Metasploit exploit. These abilities can then be found under the `metasploit` tactic. Note that this process may take 15 minutes.

If the exploit has options you want to use, you'll need to customize the ability's `command` field. Start an operation in `manual` mode, and modify the `command` field before adding the potential link to the operation. For example, to set `RHOSTS` for the exploit, modify `command` to include `set RHOSTS <MY_RHOSTS_VALUE>;` between `use <EXPLOIT_NAME>;` and `run`.

Alternatively, you can set options by adding a fact for each option with the `msf.` prefix. For example, to set `RHOST`, add a fact called `msf.RHOST`. Then in the ability's `command` field add `set RHOSTS \#{msf.RHOSTS};` between `use <EXPLOIT_NAME>;` and `run`.

## Builder

The Builder plugin enables Caldera to dynamically compile code segments into payloads that can be executed as abilities by implants. Currently, only C# is supported. 

See [Dynamically-Compiled Payloads](Dynamically-Compiled-Payloads.md) for examples on how to create abilities that leverage these payloads.

## Debrief

The Debrief plugin provides a method for gathering overall campaign information and analytics for a selected set of operations. It provides a centralized view of operation metadata and graphical displays of the operations, the techniques and tactics used, and the facts discovered by the operations. 

The plugin additionally supports the export of campaign information and analytics in PDF format.

