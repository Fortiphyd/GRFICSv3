# Getting started

MITRE Caldera, as an adversary emulation platform, can be used in several ways. For most users, it will be used to run either offensive (red) or defensive (blue) operations.

Here are the most common use-cases and basic instructions on how to proceed. 

## Autonomous red-team engagements

This is the original Caldera use-case. You can use the framework to build a specific threat (adversary) profile and launch it in a network to see where you may be susceptible. This is good for testing defenses and training blue teams on how to detect threats. 

The following steps will walk through logging in, deploying an agent, selecting an adversary, and running an operation:

1) Log in as a red user. By default, a "red" user is created with a password found in the `conf/local.yml` file (or `conf/default.yml` if using insecure settings).
1) Deploy an agent
   - Navigate to the Agents page and click the "Click here to deploy an agent"
   - Choose the Sandcat agent and platform (victim operating system)
   - Check that the value for `app.contact.http` matches the host and port the Caldera server is listening on
   - Run the generated command on the victim machine. Note that some abilities will require elevated privileges, which would require the agent to be deployed in an elevated shell.
   - Ensure that a new agent appears in the table on the Agents page
1) Choose an adversary profile
   - Navigate to the Adversaries page
   - Select an adversary from the dropdown and review abilities. The "Discovery" and "Hunter" adversaries from the Stockpile plugin are good starting profiles.
1) Run an operation
   - Navigate to the Operations page and add an operation by toggling the View/Add switch
   - Type in a name for the operation
   - Under the basic options, select a group that contains the recently deployed agent ("red" by default)
   - Under the basic options, select the adversary profile chosen in the last step
   - Click the start button to begin the operation
1) Review the operation
   - While the operation is running, abilities will be executed on the deployed agent. Click the stars next to run abilities to view the output.
1) Export operation results
   - Once the operation finishes, users can export operation reports in JSON format by clicking the "Download report"
   button in the operation GUI modal. Users can also export operation event logs in JSON format by clicking the "Download event logs"
   button in the operations modal. The event logs will also be automatically written to disk when the operation finishes.
   For more information on the various export formats and automatic/manual event log generation, see the [Operation Result page](Operation-Results.md).

Next steps may include:

- Running an operation with a different adversary profile
- Creating a new adversary profile
- Creating custom abilities and adding them to an adversary profile
- Running an operation with a different planner (such as batch)

## Autonomous incident-response 

Caldera can be used to perform automated incident response through deployed agents. This is helpful for identifying TTPs that other security tools may not see or block. 

The following steps will walk through logging in to Caldera blue, deploying a blue agent, selecting a defender, and running an operation:

1) Log in as a blue user. By default, a "blue" user is created with a password found in the `conf/local.yml` file (or `conf/default.yml` if using insecure settings).
1) Deploy a blue agent
   - Navigate to the Agents page and click the "Click here to deploy an agent"
   - Choose the Sandcat agent and platform (victim operating system)
   - Check that the value for `app.contact.http` matches the host and port the Caldera server is listening on
   - Run the generated command on the victim machine. The blue agent should be deployed with elevated privileges in most cases.
   - Ensure that a new blue agent appears in the table on the Agents page
1) Choose a defender profile
   - Navigate to the Defenders page
   - Select a defender from the dropdown and review abilities. The "Incident responder" defender is a good starting profile.
1) Choose a fact source. Defender profiles utilize fact sources to determine good vs. bad on a given host.
   - Navigate to the Sources page
   - Select a fact source and review facts. Consider adding facts to match the environment (for example, add a fact with the `remote.port.unauthorized` name and a value of `8000` to detect services running on port 8000)
   - Save the source if any changes were made
1) Run an operation
   - Navigate to the Operations page and add an operation by toggling the View/Add switch
   - Type in a name for the operation
   - Under the basic options, select a group that contains the recently deployed agent ("blue" by default)
   - Under the basic options, select the defender profile chosen previously
   - Under the autonomous menu, select the fact source chosen previously
   - Click the start button to begin the operation
1) Review the operation
   - While the operation is running, abilities will be executed on the deployed agent. Click the stars next to run abilities to view the output.
   - Consider manually running commands (or [using an automated adversary](#autonomous-red-team-engagements)) which will trigger incident response actions (such as starting a service on an unauthorized port)
1) Export operation results
   - Once the operation finishes, users can export operation reports in JSON format by clicking the "Download report"
   button in the operation GUI modal. Users can also export operation event logs in JSON format by clicking the "Download event logs"
   button in the operations modal. The event logs will also be automatically written to disk when the operation finishes.
   For more information on the various export formats and automatic/manual event log generation, see the [Operation Result page](Operation-Results.md).
   

## Manual red-team engagements

Caldera can be used to perform manual red-team assessments using the Manx agent. This is good for replacing or appending existing offensive toolsets in a manual assessment, as the framework can be extended with any custom tools you may have.

The following steps will walk through logging in, deploying a Manx agent, and running manual commands:

1) Log in as a red user
1) Deploy a Manx agent
   - Navigate to the Agents page and click the "Click here to deploy an agent"
   - Choose the Manx agent and platform (victim operating system)
   - Check that the values for `app.contact.http`, `app.contact.tcp`, and `app.contact.udp` match the host and ports the Caldera server is listening on
   - Run the generated command on the victim machine
   - Ensure that a new agent appears in the table on the Agents page
1) Deploy a Manx agent
   - Navigate to the Manx plugin
   - Select the deployed agent in the session dropdown 
   - Run manual commands in the terminal window

## Research on artificial intelligence

Caldera can be used to test artificial intelligence and other decision-making algorithms using the [Mock plugin](https://github.com/mitre/mock). The plugin adds simulated agents and mock ability responses, which can be used to run simulate an entire operation.

To use the mock plugin:

1) With the server stopped, enable the mock plugin. Restart the server.
1) Log in as a red user
1) In the Agents modal, review the simulated agents that have been spun up
1) Run an operation using any adversary against your simulated agents. Note how the operation runs non-deterministically.
1) Adjust the decision logic in a planner, such as the `batch.py` planner in the Stockpile plugin, to test out different theories
