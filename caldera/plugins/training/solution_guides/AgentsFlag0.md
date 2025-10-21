1. In the left-handside navigation, select `CAMPAIGNS > agents`.
1. Press the button `+Deploy an agent`.
1. Choose `Sandcat` agent.
1. Under Platform, choose your Operating System: Linux, Windows, or Darwin (MacOS).
1. Set `app.contact.http` value to `http://localhost:8888`.
1. In the `sh` text area click the `Copy` button to copy the displayed shell command to your clipboard. This command will instruct the agent to communicate over a HTTP channel.
1. Outside of Caldera, open a terminal window with a shell.
1. Paste the copied command into the shell and execute it.
1. Go back to Caldera and close the agent options window.
1. Wait for the agent to appear in the `Agents` table.
1. Task completed.