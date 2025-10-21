# Server Configuration

## Startup parameters

`server.py` supports the following arguments:

- `--log {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Sets the log option. The `DEBUG` option is useful for troubleshooting.
- `--fresh`: Resets all non-plugin data including custom abilities and adversaries, operations, and the agent list.
  A gzipped, tarball backup of the original content is stored in the `data/backup` directory. This makes it possible to 
  recover the server state after an accidental `--fresh` startup by running `tar -zxvf data/backup/backup-<timestamp>.tar.gz`
  from the root caldera directory before server startup.
- `--environment ENVIRONMENT`: Sets a custom configuration file. See "Custom configuration files" below for additional details.
- `--plugins PLUGINS`: Sets Caldera to run only with the specified plugins
- `--insecure`: Uses the `conf/default.yml` file for configuration, not recommended.

## Configuration file

Caldera's configuration file is located at `conf/local.yml`, written on the first run. If the server is run with the `--insecure` option (not recommended), Caldera will use the file located at `conf/default.yml`.

Configuration file changes must be made while the server is shut down. Any changes made to the configuration file while the server is running will be overwritten.

The value set for `app.frontend.api_base_url` is used to configure the Caldera v5 Vue UI when the Caldera server is started with the `--build` flag. It has been observed that in some situations the default configuration values can cause the UI to appear unresponsive due to misrouted requests. This mainly occurs when the server is running on a host different than the UI is being accessed from. In these cases, the value should be changed to the appropriate URL for the UI to route requests to.

The YAML configuration file contains all the configuration variables Caldera requires to boot up and run. A documented configuration file is below:

```yaml
ability_refresh: 60  # Interval at which ability YAML files will refresh from disk 
api_key_blue: BLUEADMIN123  # API key which grants access to Caldera blue
api_key_red: ADMIN123  # API key which grants access to Caldera red
app.contact.dns.domain: mycaldera.caldera  # Domain for the DNS contact server
app.contact.dns.socket: 0.0.0.0:53  # Listen host and port for the DNS contact server
app.contact.gist: API_KEY  # API key for the GIST contact
app.contact.html: /weather  # Endpoint to use for the HTML contact
app.contact.http: http://0.0.0.0:8888  # Server to connect to for the HTTP contact
app.contact.tcp: 0.0.0.0:7010  # Listen host and port for the TCP contact server
app.contact.udp: 0.0.0.0:7011  # Listen host and port for the UDP contact server
app.contact.websocket: 0.0.0.0:7012  # Listen host and port for the Websocket contact server
app.frontend.api_base_url: http://localhost:8888
objects.planners.default: atomic  # Specify which planner should be used by default (works for all objects, just replace `planners` with the appropriate object type name)
crypt_salt: REPLACE_WITH_RANDOM_VALUE  # Salt for file encryption
encryption_key: ADMIN123  # Encryption key for file encryption
exfil_dir: /tmp  # The directory where files exfiltrated through the /file/upload endpoint will be stored
host: 0.0.0.0  # Host the server will listen on 
plugins:  # List of plugins to enable
- access
- atomic
- compass
- debrief
- fieldmanual
- gameboard
- manx
- response
- sandcat
- stockpile
- training
port: 8888  # Port the server will listen on
reports_dir: /tmp  # The directory where reports are saved on server shutdown
auth.login.handler.module: default  # Python import path for auth service login handler ("default" will use the default handler)
requirements:  # Caldera requirements
  go:
    command: go version
    type: installed_program
    version: 1.11
  python:
    attr: version
    module: sys
    type: python_module
    version: 3.8.0
users:  # User list for Caldera blue and Caldera red
  blue:
    blue: admin  # Username and password
  red:
    admin: admin
    red: admin
```

## Custom configuration files

Custom configuration files can be created with a new file in the `conf/` directory. The name of the config file can then be specified with the `-E` flag when starting the server.

Caldera will choose the configuration file to use in the following order:

1. A config specified with the `-E` or `--environment` command-line options.  For instance, if started with `python caldera.py -E foo`, Caldera will load it's configuration from `conf/foo.yml`.
2. `conf/local.yml`: Caldera will prefer the local configuration file if no other options are specified.
3. `conf/default.yml`: If no config is specified with the `-E` option and it cannot find a `conf/local.yml` configuration file, Caldera will use its default configuration options.

## Enabling LDAP login

Caldera can be configured to allow users to log in using LDAP. To do so add an `ldap` section to the config with the following fields:

* **dn**: the base DN under which to search for the user
* **server**: the URL of the LDAP server, optionally including the scheme and port
* **user_attr**: the name of the attribute on the user object to match with the username, e.g. `cn` or `sAMAccountName`. Default: `uid`
* **group_attr**: the name of the attribute on the user object to match with the group, e.g. `MemberOf` or `group`. Default: `objectClass`
* **red_group**: the value of the group_attr that specifies a red team user. Default: `red`

For example: 

```yaml
ldap:
  dn: cn=users,cn=accounts,dc=demo1,dc=freeipa,dc=org
  server: ldap://ipa.demo1.freeipa.org
  user_attr: uid
  group_attr: objectClass
  red_group: organizationalperson
```

This will allow the `employee` user to log in as `uid=employee,cn=users,cn=accounts,dc=demo1,dc=freeipa,dc=org`. This
user has an `objectClass` attribute that contains the value `organizationalperson`, so they will be logged in as a red
team user. In contrast, the `admin` user does not have an `objectClass` of `organizationalperson` so they will be logged
in as a blue team user.

Be sure to change these settings to match your specific LDAP environment.

Note that adding the `ldap` section will disable any accounts listed in the `users` section of the config file;
only LDAP will be used for logging in.

## Setting Custom Login Handlers
By default, users authenticate to Caldera by providing credentials (username and password) in the main login page.
These credentials are verified using Caldera's internal user mapping, or via LDAP if LDAP login is enabled for Caldera.
If users want to use a different login handler, such as one that handles SAML authentication or a login handler provided
by a Caldera plugin, the `auth.login.handler.module` keyword in the Caldera configuration file
must be changed from its value of `default`, which is used to load the default login handler.
The configuration value, if not `default`, must be a Python import path string corresponding to the custom login handler relative to the main Caldera directory (e.g. `auth.login.handler.module: plugins.customplugin.app.my_custom_handler`). 
If the keyword is not provided, the default login handler will be used.

The Python module referenced in the configuration file must implement the following method:
```python
def load_login_handler(services):
    """Return Python object that extends LoginHandlerInterface from app.service.interfaces.i_login_handler"""
    pass
```

When loading custom login handlers, Caldera expects the referenced Python module to return an object that extends
`LoginHandlerInterface` from `app.service.interfaces.i_login_handler`. This interface provides all of the methods
that Caldera's authentication service requires to handle logins. If an invalid login handler is referenced in
the configuration file, then the server will exit with an error.

An example login handler Python module may follow the following structure:
```python
from app.service.interfaces.i_login_handler import LoginHandlerInterface

HANDLER_NAME = 'My Custom Login Handler'

def load_login_handler(services):
    return CustomLoginHandler(services, HANDLER_NAME)

class CustomLoginHandler(LoginHandlerInterface):
    def __init__(self, services, name):
        super().__init__(services, name)

    async def handle_login(self, request, **kwargs):
        # Handle login
        pass

    async def handle_login_redirect(self, request, **kwargs):
        # Handle login redirect
        pass
```
