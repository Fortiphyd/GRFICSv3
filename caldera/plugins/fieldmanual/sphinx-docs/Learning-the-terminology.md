# Learning the terminology

## Agents

Agents are software programs that connect back to Caldera at certain intervals to get instructions. Agents communicate with the Caldera server via a _contact_ method, initially defined at agent install.

Installed agents appear in the UI in the Agents dialog. Agents are identified by their unique _paw_ - or paw print.

Caldera includes a number of agent programs, each adding unique functionality. A few examples are listed below:

- Sandcat: A GoLang agent which can communicate through various C2 channels, such as HTTP, Github GIST, or DNS tunneling.
- Manx: A GoLang agent which communicates via the TCP contact and functions as a reverse-shell
- Ragdoll: A Python agent which communicates via the HTML contact

Agents can be placed into a _group_, either at install through command line flags or by editing the agent in the UI. These groups are used when running an operation to determine which agents to execute abilities on.

The group determines whether an agent is a "red agent" or a "blue agent". Any agent started in the "blue" group will be accessible from the blue dashboard. All other agents will be accessible from the red dashboard.

## Abilities and Adversaries 

An ability is a specific ATT&CK tactic/technique implementation which can be executed on running agents. Abilities will include the command(s) to run, the _platforms_ / _executors_ the commands can run on (ex: Windows / PowerShell), payloads to include, and a reference to a module to parse the output on the Caldera server.

Adversary profiles are groups of abilities, representing the tactics, techniques, and procedures (TTPs) available to a threat actor. Adversary profiles are used when running an operation to determine which abilities will be executed. 

## Operations

Operations run abilities on agent groups. Adversary profiles are used to determine which abilities will be run and agent groups are used to determine which agents the abilities will be run on.

The order in which abilities are run is determined by the _planner_. A few examples of planners included, by default, in Caldera are listed below:

- atomic: Run abilities in the adversary profile according to the adversary's atomic ordering 
- batch: Run all abilities in the adversary profile at once
- buckets: Run abilities in the adversary profile grouped by ATT&CK tactic

When an ability is run in an operation, a _link_ is generated for each agent if:

1. All link _facts_ and fact _requirements_ have been fulfilled
2. The agent has an executor that the ability is configured to run on
3. The agent has not yet run the ability, or the ability is marked as repeatable

A fact is an identifiable piece of information about a given computer. Fact names are referenced in ability files and will be replaced with the fact values when a link is created from the ability.

Link commands can be _obfuscated_, depending on the stealth settings of the operation.

Generated links are added to the operation _chain_. The chain contains all links created for the operation.

When an agents checks in, it will collect its instructions. The instructions are then run, depending on the _executor_ used, and results are sent back to the Caldera server.

Then the results are received, Caldera will use a _parser_ to add any collected facts to the operation. Parsers analyze the output of an ability to extract potential facts. If potential facts are allowed through the _fact rules_, the fact is added to the operation for use in future links. 

## Plugins

Caldera is a framework extended by _plugins_. These plugins provide Caldera with extra functionality in some way.

Multiple plugins are included by default in Caldera. A few noteworthy examples are below, though a more complete and detailed list can be found on the [Plugin Library](Plugin-library.md) page:

- Sandcat: The Sandcat agent is the recommended agent for new users
- Stockpile: This plugin holds the majority of open-source abilities, adversaries, planners, and obfuscators created by the Caldera team
- Training: The training plugin walks users through most of Caldera's functionality -- recommended for new users
