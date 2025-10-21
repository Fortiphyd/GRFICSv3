1. Ensure that the blue agent from the previous flag is running on a remote system
   and can communicate with the Caldera server.
1. On your local system, open a shell in a terminal.
1. Using `netcat`, open a listening TCP socket on port 7011: `nc -l 7011`
1. On the remote system running the blue agent, connect to the netcat listener created in the previous step and leave it running: `nc <IP address> 7011` (insert the correct IP address).
1. In Caldera and logged in as the blue user, click on `CAMPAIGNS > operations`.
1. In the `Operations` window, click the `+ Create Operation` button to open the `Start New Operation` menu.
1. Enter `Response Training` as the operation name.
1. Select the `Incident Responder` adversary from the `Adversary` dropdown.
1. Ensure `response` is selected in the `Fact source` dropdown.
1. Press `ADVANCED` to open the advanced options dialog.
1. Select `blue` for the group.
1. Select `Auto close operation` from the `Auto-close`radio group.
1. Select `batch` from the `Planner` dropdown.
1. Press the `Start` button.
1. Wait for the operation to complete.
1. Task completed.