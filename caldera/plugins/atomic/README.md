# MITRE Caldera plugin: Atomic

A plugin supplying Caldera with TTPs from the Atomic Red Team project.

## Details

- When importing tests from Atomic Red Team, this plugin also catches `$PathToAtomicsFolder` usages pointing to an existing file.  It then imports the files as payloads and fix path usages. Note other usages are not handled. If a path with `$PathToAtomicsFolder` points to an existing directory or an unexisting file, we will not process it any further and ingest it "as it is". Examples of such usages below:
-- https://github.com/redcanaryco/atomic-red-team/blob/a956d4640f9186a7bd36d16a63f6d39433af5f1d/atomics/T1022/T1022.yaml#L99
-- https://github.com/redcanaryco/atomic-red-team/blob/ab0b391ac0d7b18f25cb17adb330309f92fa94e6/atomics/T1056/T1056.yaml#L24

- ART tests only specify techniques they address. This plugin creates a mapping and import abilities under the corresponding tactic.  Yet sometimes multiple tactics are a match, and we do not know which one the test addresses. This will be fixed in the future thanks to the ATT&CK sub-techniques. As of now, we use a new tactic category called "multiple".

## Known issues
- When a command/cleanup expands over multiple lines with one of them being a comment, it messes up the whole command/cleanup (as we reduce multiple lines into one with semi-colons).

## Acknowledgements

- [Atomic Red Team](https://github.com/redcanaryco/atomic-red-team)
- [AtomicCaldera](https://github.com/xenoscr/atomiccaldera)
