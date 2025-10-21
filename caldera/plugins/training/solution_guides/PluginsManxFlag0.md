1. Launching the agent:
    1. In the left-handside navigation, select `CAMPAIGNS > agents`.
    1. Press the button `+Deploy an agent`.
    1. Choose `Manx` agent.
    1. Choose Linux platform.
    1. Update the `app.contact.http` value to specify an IP address of `127.0.0.1` (keep the port). This is for downloading the agent binary.
    1. Update the `app.contact.tcp` value to specify an IP address of `127.0.0.1` (keep the port). This is for the agent communication channel.
    1. In the `sh` text area labeled `A reverse-shell agent which communicates via the TCP contact`, click the `Copy` button to copy the displayed shell command to your clipboard. 
1. Run two remote shell commands:
    1. On your local system and outside of Caldera, open a shell in a terminal.
    1. Paste the copied command and execute it.
    1. Wait for the agent to appear in the `Agents` table.
    1. In the left-handside navigation, select `PLUGINS > manx`
    1. Select the Agent session from the `Select a session` dropdown. This should populate the remote shell window with a prompt.
    1. In the remote shell, type `whoami` and press enter.
    1. In the remote shell, type `uname -a` and press enter.
1. Run `Check` operation:
    1. In the left-handside navigation, select `CAMPAIGNS > operations`.
    1. Click the `+ Create Operation` button to open the `Start New Operation` menu.
    1. Give the operation a name.
    1. Select the `Check` adversary from the `Adversary` dropdown.
    1. Select `basic` from the `Fact source` menu.
    1. Press `ADVANCED` to open the advanced options dialog.
    1. Select `Auto close operation` from the `Auto-close`radio group.
    1. Press `Start` to run the operation.
    1. Wait for the operation to complete.
    1. If the `Auto close operation` option was not selected, press the stop button to finish the operation.
1. Task completed.
