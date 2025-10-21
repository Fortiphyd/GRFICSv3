1. In the left-handside navigation, select `CAMPAIGNS > agents`.
1. Press the button `+Deploy an agent`.
1. Choose `Manx` agent.
1. Choose Linux platform.
1. Update the `app.contact.http` value to specify an IP address of `127.0.0.1` (keep the port). This is for downloading the agent binary.
1. Update the `app.contact.udp` value to specify an IP address of `127.0.0.1` (keep the port). This is for the agent-C2 communication channel.
1. In the `sh` text area labeled `Run against the UDP contact`, click the `Copy` button to copy the displayed shell command to your clipboard. 
1. On your local system and outside of Caldera, open a shell in a terminal.
1. Paste the copied command and execute it.
1. Wait for the agent to appear in the `Agents` table.
1. Task completed.
