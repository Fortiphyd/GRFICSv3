1. In the left-handside navigation, select `CAMPAIGNS > agents`.
1. Press the `+Deploy an agent` button.
1. Choose Manx agent.
1. In the Platform selector, select your Operating System.
1. Update the `app.contact.http` value to specify `localhost` (keep the port). For example: `http://localhost:8888`. This is for downloading the agent binary.
1. Update the `app.contact.tcp` value to specify `localhost` (keep the port). For example: `localhost:7010`. This is for the agent-C2 communication channel.
1. In the `sh` text area click the `Copy` button to copy the displayed shell command to your clipboard. This command will instruct the agent to communicate over a TCP channel.
1. On your local system and outside of Caldera, open a shell in a terminal.
1. Paste the copied command and execute it.
1. Wait for the agent to appear in the `Agents` table.
1. Task completed.