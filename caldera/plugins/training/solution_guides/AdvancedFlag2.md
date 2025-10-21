1. Terminate the Caldera server.
1. Edit the `conf/local.yml` file in your preferred text editor. If this file does not exist, ensure the Caldera server is not run with the `--insecure` flag and run and terminate the server again.
1. Add the following entry to the `users > red` section: `test: test`.
1. Re-run the server. Ensure the `--fresh` flag is not used.
1. Task completed.