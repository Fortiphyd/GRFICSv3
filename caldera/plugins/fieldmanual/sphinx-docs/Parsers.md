# Parsers

Caldera uses parsers to extract facts from command output. A common use case is to allow
operations to take gathered information and feed it into future abilities and decisions -
for example, a discovery ability that looks for sensitive files can output file paths, which
will then be parsed into file path facts, and a subsequent ability can use those file paths
to stage the sensitive files in a staging directory.

Parsers can also be used to create facts with relationships linked between them - this allows
users to associate facts together, such as username and password facts. 

Under the hood, parsers are python modules that get called when the agent sends command output 
to the Caldera server and certain conditions are met:
- If the corresponding ability has a specified parser associated with the command, 
the parser module will be loaded and used to parse out any facts from the output.
This will occur even if the agent ran the command outside of an operation
- If the agent ran the command as part of an operation, but the corresponding ability does not 
have any specified parsers associated with the command, Caldera will check if the operation
was configured to use default parsers. If so, any default parsers loaded within Caldera will
be used to parse out facts from the output. Otherwise, no parsing occurs.
- If the agent ran the command outside of an operation, but the corresponding ability does not
have any specified parsers associated with the command, Caldera will use its default parsers
to parse the output.

Non-default Parser python modules are typically stored in individual plugins, such as `stockpile`, in the
plugin's `app/parsers/` directory. For instance, if you look in `plugins/stockpile/app/parsers`, 
you can see a variety of parsers that are provided out-of-the-box.

Default parsers are located in the core Caldera repo, under `app/learning`. 
Two example modules are `p_ip.py` and `p_path.py`, which are used to parse IP addresses and file
paths, respectively. Note that the default parsers have a different location due to their
association with the learning service.
 

## Linking Parsers to an Ability
To associate specific parsers to an ability command, use the `parsers` keyword in the yaml file
within the executor section (see the below example).

```yaml
    darwin:
      sh:
        command: |
          find /Users -name '*.#{file.sensitive.extension}' -type f -not -path '*/\.*' -size -500k 2>/dev/null | head -5
        parsers:
          plugins.stockpile.app.parsers.basic:
            - source: host.file.path
              edge: has_extension
              target: file.sensitive.extension
```

Note that the parsers value is a nested dictionary whose key is the Python module import path 
of the parser to reference; in this case, `plugins.stockpile.app.parsers.basic` for the Parser 
located in `plugins/stockpile/app/parsers/basic.py`. 
The value of this inner dict is a list of fact mappings that tell the Parser what facts and 
relationships to save based on the output. In this case, we only have one mapping in the list.

Each mapping consists of the following:
- **Source** (required): A fact to create for any matches from the parser

- **Edge** (optional): A relationship between the source and target. This should be a string.

- **Target** (optional): A fact to create which the source connects to.

In the above example, the `basic` parser will take each line of output from the `find` command,
save it as a `host.file.path` fact, and link it to the `file.sensitive.extension` fact used in 
the command with the `has_extension` edge. For instance, if the command was run using a 
`file.sensitive.extension` value of `docx` and the `find` command returned `/path/to/mydoc.docx`
and `/path/to/sensitive.docx`, the parser would generate the following facts and relationships:
- `/path/to/mydoc.docx` <- `has_extension` -> `docx`
- `/path/to/sensitive.docx` <- `has_extension` -> `docx`

Note that only one parser can be linked to a command at a time, though a single parser can be used to
generate multiple facts, as in our hypothetical example above. Also note that the parser only works
for the associated command executor, so you can use different parsers for different executors and
even different platforms. 

The example below shows a more complicated parser - the `katz` parser in the `stockpile` plugin.
This example has multiple fact mappings for a single parser, since we want to extract different
types of information from the Mimikatz output - in particular, the password and password hash 
information.

```yaml
  platforms:
    windows:
      psh:
        command: |
          Import-Module .\invoke-mimi.ps1;
          Invoke-Mimikatz -DumpCreds
        parsers:
          plugins.stockpile.app.parsers.katz:
          - source: domain.user.name
            edge: has_password
            target: domain.user.password
          - source: domain.user.name
            edge: has_hash
            target: domain.user.ntlm
          - source: domain.user.name
            edge: has_hash
            target: domain.user.sha1
        payloads:
        - invoke-mimi.ps1
```

This time, we are using `plugins.stockpile.app.parsers.katz`, which will take the output
from the `Invoke-Mimikatz -DumpCreds` command and apply the 3 specified mappings when parsing
the output. Note that in all 3 mappings, the source fact is the same: `domain.user.name`, but
the relationship edges and target facts are all different, based on what kind of information we
want to save. The resulting facts, assuming the command was successful and provided the desired
information, will include the username, password, NTLM hash, and SHA1 hash, all linked together
with the appropriate relationship edges.
