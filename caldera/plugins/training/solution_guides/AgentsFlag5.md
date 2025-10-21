1. Open a shell in a terminal outside of Caldera.
1. In that shell, navigate to your caldera folder: `cd /path/to/caldera`.
1. Run `grep -R 'command: whoami' plugins/stockpile/data/abilities` at look for matching files.
1. Open `plugins/stockpile/data/abilities/discovery/c0da588f-79f0-4263-8998-7496b1a40596.yml`.
  in a text editor and confirm that it runs `whoami` as a command.
1. Copy the `name` portion of the yml ability file to your clipboard: (it should say `Identify active user`).
1. In Caldera browser window, select `CAMPAIGNS > agents`.
1. Press the `Configuration` button to open `Agent Configuration` window.
1. Click the `+` next to Bootstrap Abilities.
1. Text search box opens below.
1. Paste the ability name in the text search box and click to select the found ability.
1. Press the `Save` button.
1. Task completed.