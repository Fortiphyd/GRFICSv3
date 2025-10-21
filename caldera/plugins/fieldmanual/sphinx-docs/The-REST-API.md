# The REST API

```{warning}
The original REST API has been deprecated. The new REST API v2 documentation can be found in the CORE SYSTEM API section or by scrolling to the bottom of the Caldera navigation menu and selecting "api docs."
```

### /api/rest

You can interact with all parts of Caldera through the core REST API endpoint /api/rest. If you
send requests to "localhost" - you are not required to pass a key header. If you send requests to
127.0.0.1 or any other IP addresses, the key header is required. You can set the API key in the 
conf/default.yml file. Some examples below will use the header, others will not, for example.

> Any request to this endpoint must include an "index" as part of the request, which routes it to the appropriate object type. 

Here are the available REST API functions:

## Agents

#### DELETE

Delete any agent. 
```
curl -H "KEY:$API_KEY" -X DELETE http://localhost:8888/api/rest -d '{"index":"agents","paw":"$agent_paw"}'
```

#### POST

View the abilities a given agent could execute.
```
curl -H "KEY:$API_KEY" -X POST localhost:8888/plugin/access/abilities -d '{"paw":"$PAW"}'
```

Execute a given ability against an agent, outside the scope of an operation. 
```
curl -H "KEY:$API_KEY" -X POST localhost:8888/plugin/access/exploit -d '{"paw":"$PAW","ability_id":"$ABILITY_ID","obfuscator":"plain-text"}'
```
> You can optionally POST an obfuscator and/or a facts dictionary with key/value pairs to fill in any variables the chosen ability requires.
```
{"paw":"$PAW","ability_id":"$ABILITY_ID","obfuscator":"base64","facts":[{"trait":"username","value":"admin"},{"trait":"password", "value":"123"}]}
```

## Adversaries

View all abilities for a specific adversary_id (the UUID of the adversary).
```
curl -H "KEY:$API_KEY" 'http://localhost:8888/api/rest' -H 'Content-Type: application/json' -d '{"index":"adversaries","adversary_id":"$adversary_id"}'
```

View all abilities for all adversaries.
```
curl -H "KEY:$API_KEY" 'http://localhost:8888/api/rest' -H 'Content-Type: application/json' -d '{"index":"adversaries"}'
```

## Operations

#### DELETE

Delete any operation. Operation ID must be a integer.
```bash
curl -H "KEY:$API_KEY" -X DELETE http://localhost:8888/api/rest -d '{"index":"operations","id":"$operation_id"}'
```

#### POST

Change the state of any operation. In addition to finished, you can also use: paused, run_one_link or running.
```bash
curl -X POST -H "KEY:$API_KEY" http://localhost:8888/api/rest -d '{"index":"operation", "op_id":123, "state":"finished"}'
```

#### PUT

Create a new operation. All that is required is the operation name, similar to creating a new operation
in the browser.
```bash
curl -X PUT -H "KEY:$API_KEY" http://127.0.0.1:8888/api/rest -d '{"index":"operations","name":"testoperation1"}'
```
Optionally, you can include:

1) group (defaults to empty string)
2) adversary_id (defaults to empty string)
3) planner (defaults to *batch*)
4) source (defaults to *basic*')
5) jitter (defaults to *2/8*)
6) obfuscator (defaults to *plain-text*)
7) visibility (defaults to *50*)
8) autonomous (defaults to *1*)
9) phases_enabled (defaults to *1*)
10) auto_close (defaults to *0*)

To learn more about these options, read the "What is an operation?" documentation section.           

## /file/upload

Files can be uploaded to Caldera by POST'ing a file to the /file/upload endpoint. Uploaded files will be put in the exfil_dir location specified in the default.yml file.

#### Example
```bash
curl -F 'data=@path/to/file' http://localhost:8888/file/upload
```

## /file/download

Files can be downloaded from Caldera through the /file/download endpoint. This endpoint requires an HTTP header called "file" with the file name as the value. When a file is requested, Caldera will look inside each of the payload directories listed in the local.yml file until it finds a file matching the name.

Files can also be downloaded indirectly through the [payload block of an ability](Learning-the-terminology.md).

> Additionally, the [Sandcat plugin](Plugin-library.md) delivery commands utilize the file download endpoint to drop the agent on a host

#### Example
```bash
curl -X POST -H "file:wifi.sh" http://localhost:8888/file/download > wifi.sh
```
