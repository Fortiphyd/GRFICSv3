1. Log into Caldera as a `blue` group user (by default, the username is `blue`).
1. In the left-handside navigation, select `CAMPAIGNS > agents`.
1. Press the button `+ Deploy an agent`.
1. Choose `Sandcat` agent.
1. Under Platform, choose Linux.
1. Update the `app.contact.http` value to specify an IP address of the Caldera server that is reachable from the remote system (e.g. `10.0.2.2`). Keep the port value unchanged.
1. In the `sh` text area click the `Copy` button to copy the displayed second shell command `Deploy as a blue-team agent instead of red` to your clipboard. This command will instruct the agent to communicate over a HTTP channel.
1. On the remote system, open a terminal with a shell.
1. Paste the copied command into the shell and execute it.
1. Go back to Caldera and close the `Deploy an agent` window.
1. Wait for the agent to appear in the `Agents` table.
1. Task completed.