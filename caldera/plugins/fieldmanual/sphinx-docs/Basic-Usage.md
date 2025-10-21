
# Basic Usage

## Agents

### Agent Management

To deploy an agent:

1. Navigate to the Agents module in the side menu under "Campaigns" and click the "Deploy an agent" button
1. Choose an agent (Sandcat is a good one to start with) and a platform (target operating system)
1. Make sure the agent options are correct (e.g. ensure `app.contact.http` matches the expected host and port for the Caldera server)
    - `app.contact.http` represents the HTTP endpoint (including the IP/hostname and port) that the C2 server is listening on for
    agent requests and beacons. Examples: `http://localhost:8888`, `https://10.1.2.3`, `http://myc2domain.com:8080`
    - `agents.implant_name` represents the base name of the agent binary. 
    For Windows agents, `.exe` will be automatically appended to the base name (e.g. `splunkd` will become `splunkd.exe`).
    - `agent.extensions` takes in a comma-separated list of agent extensions to compile with your agent binary.
    When selecting the associated deployment command, this will instruct the C2 server to compile the agent binary with the 
    requested extensions, if they exist. If you just want a basic agent without extensions, leave this field blank.
    See [Sandcat extension documentation](plugins/sandcat/Sandcat-Details.md#extensions) for more information on Sandcat
    extensions.
1. Choose a command to execute on the target machine. If you want your agent to be compiled with the
 extensions from `agent.extensions`, you must select the associated deployment command below: 
 `Compile red-team agent with a comma-separated list of extensions (requires GoLang).`
1. On the target machine, paste the command into the terminal or PowerShell window and execute it
1. The new agent should appear in the table in the Agents tab (if the agent does not appear, check the [Agent Deployment section of the Troubleshooting page](Troubleshooting.md#agent-deployment))

To kill an agent, use the "Kill Agent" button under the agent-specific settings. The agent will terminate on its next beacon.

To remove the agent from Caldera (will not kill the agent), click the red X. Running agents remove from Caldera will reappear when they check in.

### Agent Settings

Several configuration options are available for agents:

* **Beacon Timers**: Set the minimum and maximum seconds the agent will take to beacon home. These timers are applied to all newly-created agents.
* **Watchdog Timer**: Set the number of seconds to wait, once the server is unreachable, before killing an agent. This timer is applied to all newly-created agents.
* **Untrusted Timer**: Set the number of seconds to wait before marking a missing agent as untrusted. Operations will not generate new links for untrusted agents. This is a global timer and will affect all running and newly-created agents.
* **Implant Name**: The base name of newly-spawned agents. If necessary, an extension will be added when an agent is created (e.g. `splunkd` will become `splunkd.exe` when spawning an agent on a Windows machine).
* **Bootstrap Abilities**: A comma-separated list of ability IDs to be run on a new agent beacon. By default, this is set to run a command which clears command history.
* **Deadman Abilities**: A comma-separated list of ability IDs to be run immediately prior to agent termination. The agent must support deadman abilities in order for them to run.

Agents have a number of agent-specific settings that can be modified by clicking on the button under the 'PID' column for the agent:

* **Group**: Agent group
* **Sleep**: Beacon minimum and maximum sleep timers for this specific agent, separated by a forward slash (`/`)
* **Watchdog**: The watchdog timer setting for this specific agent

## Abilities

The majority of abilities are stored inside the Stockpile plugin (`plugins/stockpile/data/abilities`), along the adversary profiles which use them. Abilities created through the UI will be placed in `data/abilities`.

Here is a sample ability:
```
- id: 9a30740d-3aa8-4c23-8efa-d51215e8a5b9
  name: Scan WIFI networks
  description: View all potential WIFI networks on host
  tactic: discovery
  technique:
    attack_id: T1016
    name: System Network Configuration Discovery
  platforms:
    darwin:
      sh:
        command: |
          ./wifi.sh scan
        payload: wifi.sh
    linux:
      sh:
        command: |
          ./wifi.sh scan
        payload: wifi.sh
    windows:
      psh:
        command: |
          .\wifi.ps1 -Scan
        payload: wifi.ps1
```

Things to note:
* Each ability has a random UUID id
* Each ability requires a name, description, ATT&CK tactic and technique information
* Each ability requires a platforms list, which should contain at least 1 block for a supported operating system (platform). Currently, abilities can be created for Windows, Linux, and Darwin (MacOS).
* Abilities can be added to an adversary through the GUI with the 'add ability' button
* The delete_payload field (optional, placed at the top level, expects True or False) specifies whether the agent should remove the payload from the filesystem after the ability completes. The default value, if not provided, is True.
* The singleton field (optional, placed at the top level, expects True or False) specifies that the ability should only be run successfully once - after it succeeds, it should not be run again in the same operation. The default value, if not provided, is False.
* The repeatable field (optional, placed at the top level, expects True or False) specifies that the ability can be repeated as many times as the planner desires. The default value, if not provided, is False.

Please note that only one of singleton or repeatable should be True at any one time - singleton operates at an operational level, and repeatable at an agent level. If both are true at the same time, Caldera may behave unexpected.

For each platform, there should be a list of executors. In the default Sandcat deployment, Darwin and Linux platforms can use sh and Windows can use psh (PowerShell) or cmd (command prompt).

Each platform block consists of a:
* command (required)
* payload (optional)
* uploads (optional)
* cleanup (optional)
* parsers (optional)
* requirements (optional)
* timeout (optional)

**Command**: A command can be 1-line or many and should contain the code you would like the ability to execute. Newlines in the command will be deleted before execution. The command can (optionally) contain variables, which are identified as `#{variable}`.

Prior to execution of a command, Caldera will search for variables within the command and attempt to replace them with values. The values used for substitution depend on the type of the variable in the command: user-defined or global variable. User-defined variables are associated with facts can be filled in with fact values from fact sources or parser output, while _global  variables_ are filled in by Caldera internally and cannot be substituted with fact values.

The following global variables are defined within Caldera:

* `#{server}` references the FQDN of the Caldera server itself. Because every agent may know the location of Caldera differently, using the `#{server}` variable allows you to let the system determine the correct location of the server.
* `#{group}` is the group a particular agent is a part of. This variable is mainly useful for lateral movement, where your command can start an agent within the context of the agent starting it.
* `#{paw}` is the unique identifier - or paw print - of the agent.
* `#{location}` is the location of the agent on the client file system.
* `#{exe_name}` is the executable name of the agent.
* `#{upstream_dest}` is the address of the immediate "next hop" that the agent uses to reach the Caldera server. For agents that directly connect to the server, this will be the same as the `#{server}` value. For agents that use peer-to-peer, this value will be the peer address used.
* `#{origin_link_id}` is the internal link ID associated with running this command used for agent tracking.
* `#{payload}` and `#{payload:<uuid>}` are used primarily in cleanup commands to denote a payload file downloaded by an agent.
* `#{app.*}` are configuration items found in your main Caldera configuration (e.g., `conf/default.yml`) with a prefix of `app.`. Variables starting with `app.` that are not found in the Caldera configuration are not treated as global variables and can be subject to fact substitution.

**Payload**: A comma-separated list of files which the ability requires in order to run. In the windows executor above, the payload is wifi.ps1. This means, before the ability is used, the agent will download wifi.ps1 from Caldera. If the file already exists, it will not download it. You can store any type of file in the payload directories of any plugin.

> Did you know that you can assign functions to execute on the server when specific payloads are requested for download? An example of this is the sandcat.go file. Check the plugins/sandcat/hook.py file to see how special payloads can be handled.

Payloads can be stored as regular files or you can xor (encode) them so the anti-virus on the server-side does not pick them up. To do this, run the app/utility/payload_encoder.py against the file to create an encoded version of it. Then store and reference the encoded payload instead of the original.

> The payload_encoder.py file has a docstring which explains how to use the utility.

Payloads also can be ran through a packer to obfuscate them further from detection on a host machine.  To do this you would put the packer module name in front of the filename followed by a colon ':'.  This non-filename character will be passed in the agent's call to the download endpoint, and the file will be packed before sending it back to the agent. UPX is currently the only supported packer, but adding addition packers is a simple task.

> An example for setting up for a packer to be used would be editing the filename in the payload section of an ability file: - upx:Akagi64.exe

**Uploads**: A list of files which the agent will upload to the C2 server after running the ability command. The filepaths can be specified as local file paths or absolute paths. The ability assumes that these files will exist during the time of upload.

Below is an example ability that uses the `uploads` keyword:

```
---

- id: 22b9a90a-50c6-4f6a-a1a4-f13cb42a26fd
  name: Upload file example
  description: Example ability to upload files
  tactic: exfiltration
  technique:
    attack_id: T1041
    name: Exfiltration Over C2 Channel
  platforms:
    darwin,linux:
      sh:
        command: |
          echo "test" > /tmp/absolutepath.txt;
          echo "test2" > ./localpath.txt;
        cleanup: |
          rm -f /tmp/absolutepath.txt ./localpath.txt;
        uploads:
          - /tmp/absolutepath.txt
          - ./localpath.txt
```

**Cleanup**: An instruction that will reverse the result of the command. This is intended to put the computer back into the state it was before the ability was used. For example, if your command creates a file, you can use the cleanup to remove the file. Cleanup commands run after an operation, in the reverse order they were created. Cleaning up an operation is also optional, which means you can start an operation and instruct it to skip all cleanup instructions. 

Cleanup is not needed for abilities, like above, which download files through the payload block. Upon an operation completing, all payload files will be removed from the client (agent) computers.

**Parsers**: A list of parsing modules which can parse the output of the command into new facts. Interested in this topic? Check out [how Caldera parses facts](Parsers.md), which goes into detail about parsers. 

Abilities can also make use of two Caldera REST API endpoints, file upload and download.

**Requirements**: Required relationships of facts that need to be established before this ability can be used. See [Requirements](Requirements.md) for more information.

**Timeout**: How many seconds to allow the command to run.

### Bootstrap and Deadman Abilities 

Bootstrap Abilities are abilities that run immediately after sending their first beacon in. A bootstrap ability can be added through the GUI by entering the ability id into the 'Bootstrap Abilities' field in the 'Agents' tab. Alternatively, you can edit the `conf/agents.yml` file and include the ability id in the bootstrap ability section of the file (ensure the server is turned off before editing any configuration files).

Deadman Abilities are abilities that an agent runs just before graceful termination. When the Caldera server receives an initial beacon from an agent that supports deadman abilities, the server will immediately send the configured deadman abilities, along with any configured bootstrap abilities, to the agent. The agent will save the deadman abilities and execute them if terminated via the GUI or if self-terminating due to watchdog timer expiration or disconnection from the C2. Deadman abilities can be added through the GUI by entering a comma-separated list of ability IDs into the 'Deadman Abilities' field in the 'Agents' tab. Alternatively, you can edit the 'conf/agents.yml' file and include the ability ID in the 'deadman_abilities' section of the file (ensure the server is turned off before editing any configuration files).

Below is an example `conf/agents.yml` file with configured bootstrap and deadman abilities:

```
bootstrap_abilities:
- 43b3754c-def4-4699-a673-1d85648fda6a # Clear and avoid logs
deadman_abilities:
- 5f844ac9-5f24-4196-a70d-17f0bd44a934 # delete agent executable upon termination
implant_name: splunkd
sleep_max: 60
sleep_min: 30
untrusted_timer: 90
watchdog: 0
deployments:
  - 2f34977d-9558-4c12-abad-349716777c6b #Sandcat
  - 356d1722-7784-40c4-822b-0cf864b0b36d #Manx
  - 0ab383be-b819-41bf-91b9-1bd4404d83bf #Ragdoll
```

## Adversary Profiles

The majority of adversary profiles are stored inside the Stockpile plugin (`plugins/stockpile/data/adversaries`). Adversary profiles created through the UI will be placed in `data/adversaries`.

Adversaries consist of an objective (optional) and a list of abilities under atomic_ordering. This ordering determines the order in which abilities will be run.

An example adversary is below:

```
id: 5d3e170e-f1b8-49f9-9ee1-c51605552a08
name: Collection
description: A collection adversary
objective: 495a9828-cab1-44dd-a0ca-66e58177d8cc
atomic_ordering:
    - 1f7ff232-ebf8-42bf-a3c4-657855794cfe #find company emails
    - d69e8660-62c9-431e-87eb-8cf6bd4e35cf #find ip addresses
    - 90c2efaa-8205-480d-8bb6-61d90dbaf81b #find sensitive files
    - 6469befa-748a-4b9c-a96d-f191fde47d89 #create staging dir
```

## Operations

An operation can be started with a number of optional configurations:

* **Group**: Which collection of agents would you like to run against
* **Adversary**: Which adversary profile would you like to run
* **Auto-close**: Automatically close the operation when there is nothing left to do. Alternatively, keep the operation forever.
* **Run immediately**: Run the operation immediately or start in a paused state
* **Autonomous**: Run autonomously or manually. Manual mode will ask the operator to approve or discard each command.
* **Planner**: You can select which logic library - or planner - you would like to use.
* **Fact source**: You can attach a source of facts to an operation. This means the operation will start with "pre-knowledge" of the facts, which it can use to fill in variables inside the abilities.
* **Cleanup timeout**: How many seconds to wait for each cleanup command to complete before continuing.
* **Obfuscators**: Select an obfuscator to encode each command with, before they are sent to the agents.
* **Jitter**: Agents normally check in with Caldera every 60 seconds. Once they realize they are part of an active operation, agents will start checking in according to the jitter time, which is by default 2/8. This fraction tells the agents that they should pause between 2 and 8 seconds (picked at random each time an agent checks in) before using the next ability. 
* **Visibility**: How visible should the operation be to the defense. Defaults to 51 because each ability defaults to a visibility of 50. Abilities with a higher visibility than the operation visibility will be skipped.

After starting an operation, users can export the operation report in JSON format by clicking the "Download report" button in the operation GUI modal. For more information on the operation report format, see the [Operation Result](Operation-Results.md) section.

## Facts

A fact is an identifiable piece of information about a given computer. Facts can be used to perform variable assignment within abilities.

Facts are composed of the following:

* **name**: a descriptor which identifies the type of the fact and can be used for variable names within abilities. Example: `host.user.name`. Note that Caldera 3.1.0 and earlier required fact names/traits to be formatted as `major.minor.specific` but this is no longer a requirement.
* **value**: any arbitrary string. An appropriate value for a `host.user.name` may be "Administrator" or "John".
* **score**: an integer which associates a relative importance for the fact. Every fact, by default, gets a score of 1. If a `host.user.password` fact is important or has a high chance of success if used, you may assign it a score of 5. When an ability uses a fact to fill in a variable, it will use those with the highest scores first. If a fact has a score of 0, it will be blocklisted - meaning it cannot be used in the operation.

> If a property has a prefix of `host.` (e.g., `host.user.name`) you can ensure that the fact will only be used by the host that collected it if you add the `plugins.stockpile.app.requirements.paw_provenance` requirement to the ability using the fact.

As hinted above, when Caldera runs abilities, it scans the command and cleanup instructions for variables. When it finds one, it then looks at the facts it has and sees if it can replace the variables with matching facts (based on the property). It will then create new variants of each command/cleanup instruction for each possible combination of facts it has collected. Each variant will be scored based on the cumulative score of all facts inside the command. The highest scored variants will be executed first.

Facts can be added or modified through the GUI by navigating to *Advanced -> Sources* and clicking on '+ add row'.

## Fact sources

A fact source is a collection of facts that you have grouped together. A fact source can be applied to an operation when you start it, which gives the operation facts to fill in variables with. 

Fact sources can be added or modified through the GUI by navigating to *Advanced -> Sources*.

## Rules

A rule is a way of restricting or placing boundaries on Caldera. Rules are directly related to facts and should be included in a fact sheet.

Rules act similar to firewall rules and have three key components: fact, action, and match

1. **Fact** specifies the name of the fact that the rule will apply to
2. **Action** (ALLOW, DENY) will allow or deny the fact from use if it matches the rule
3. **Match** regex rule on a fact's value to determine if the rule applies

During an operation, the planning service matches each link against the rule-set, discarding it if any of the fact assignments in the link match a rule specifying DENY and keeping it otherwise. In the case that multiple rules match the same fact assignment, the last one listed will be given priority.

**Example**

```
rules:
  - action: DENY
    fact: file.sensitive.extension
    match: .*
  - action: ALLOW
    fact: file.sensitive.extension
    match: txt
```

In this example only the txt file extension will be used. Note that the ALLOW action for txt supersedes the DENY for all, as the ALLOW rule is listed later in the policy. If the ALLOW rule was listed first, and the DENY rule second, then all values (including txt) for file.sensitive.extension would be discarded.

### Subnets

Rules can also match against subnets.

**Subnet Example**

```
  - action: DENY
    fact: my.host.ip
    match: .*
  - action: ALLOW
    fact: my.host.ip
    match: 10.245.112.0/24
```

In this example, the rules would permit Caldera to only operate within the 10.245.112.1 to 10.245.112.254 range.

Rules can be added or modified through the GUI by navigating to *Advanced -> Sources* and clicking on '+ view rules'.

### Fact Source Adjustments

Fact source adjustments allow for dynamic adjustment specific ability's `visibility` in the context of an operation.

**Adjustment Example (`basic` fact source)**

```
  adjustments:
    1b4fb81c-8090-426c-93ab-0a633e7a16a7:
      host.installed.av:
        - value: symantec
          offset: 3
        - value: mcafee
          offset: 3
```

In this example, if in the process of executing an operation, a `host.installed.av` fact was found with either the value `symantec` or `mcafee`, ability `1b4fb81c-8090-426c-93ab-0a633e7a16a7` (Sniff network traffic) would have its visibility score raised and the status `HIGH_VIZ`.  This framework allows dynamic adjustments to expected ability visibility based on captured facts (in this example the presence of anti-virus software on the target) which may impact our desire to run the ability, as it might be more easily detected in this environment.

When the "Sniff network traffic" ability is run, its visibility is *only* adjusted if, at the time of execution, the fact source has a `host.installed.av` fact with either the value `symantec` or `mcafee`.  If one or both of these facts are present, each execution of "Sniff network traffic" will have `3` (the value of it's `offset`) added to its visibility score.  This visibility adjustment is recorded in the operation report.

Adjustments must be added or modified through the fact source's `.yml` file, with the exception of new fact sources created using the REST API's `sources` endpoint with a well-formed `PUT` request.

## Planners

A planner is a module within Caldera which contains logic for how a running operation should make decisions about which abilities to use and in what order.

Planners are single module Python files. Planners utilize the core system’s planning_svc.py, which has planning logic useful for various types of planners.

### The Atomic planner

Caldera ships with a default planner, _atomic_. The _atomic_ planner operates by atomically sending a single ability command to each agent in the operation's group at a time, progressing through abilities as they are enumerated in the underlying adversary profile. When a new agent is added to the operation, the _atomic_ planner will start with the first ability in the adversary profile.

The _atomic_ planner can be found in the `mitre/stockpile` GitHub repository at `app/atomic.py`.
 
### Custom Planners

For any other planner behavior and functionality, a custom planner is required. Caldera has open sourced some custom planners, to include the _batch_ and _buckets_ planners. From time to time, the Caldera team will open source further planners as they become more widely used, publicly available, etc.

The _batch_ planner will retrieve all ability commands available and applicable for the operation and send them to the agents found in the operation's group. The _batch_ planner uses the planning service to retrieve ability commands based on the chosen advsersary and known agents in the operation. The abilities returned to the _batch_ planner are based on the agent matching the operating system (execution platform) of the ability and the ability command having no unsatisfied facts. The _batch_ planner will then send these ability commands to the agents and wait for them to be completed. After each batch of ability commands is completed, the _batch_ planner will again attempt to retrieve all ability commands available for the operation and attempt to repeat the cycle. This is required as once ability commands are executed, new additional ability commands may also become unlocked; e.g. required facts being present now, newly spawned agents, etc. The _batch_ planner should be used for profiles containing repeatable abilities.

The _buckets_ planner is an example planner to demonstrate how to build a custom planner as well as the planning service utilities available to planners to aid in the formation decision logic.

The _batch_ and _buckets_ planners can be found in the `mitre/stockpile` github repository at `app/batch.py` and `app/buckets.py`.

See [How to Build Planners](How-to-Build-Planners.md) for full walkthrough of how to build a custom planner and incorporate any custom decision logic that is desired.

### Repeatable Abilities and Planners

When creating a new operation, selecting a profile with repeatable abilities will disable both the _atomic_ and the _buckets_ planners. Due to the behavior and functionality of these planners, repeatable abilities will result in the planner looping infinitely on the repeatable ability. It is recommended to use the _batch_ planner with profiles containing repeatable abilities.

## Plugins

Caldera is built using a plugin architecture on top of the core system. Plugins are separate git repositories that plug new features into the core system. Each plugin resides in the plugins directory and is loaded into Caldera by adding it to the local.yml file.

Plugins can be added through the UI or in the configuration file (likely `conf/local.yml`). Changes to the configuration file while the server is shut down. The plugins will be enabled when the server restarts.

Each plugin contains a single hook.py file in its root directory. This file should contain an initialize function, which gets called automatically for each loaded plugin when Caldera boots. The initialize function contains the plugin logic that is getting "plugged into" the core system. This function takes a single parameter:

- **services**: a list of core services that live inside the core system. 

A plugin can add nearly any new functionality/features to Caldera by using the two objects above. 

A list of plugins included with Caldera can be found on the [Plugin library](Plugin-library.md) page.
