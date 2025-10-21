# Stockpile: Exfiltration Walkthrough

This document will discuss how to utilize various exfiltration abilities within Caldera, specifically focused on the
following abilities:

- Advanced File Search and Stager
- Find Git Repositories & Compress Git Repository (local host)
- Compress Staged Directory (Password Protected) – 7z and tar+gpg
- Compress Staged Directory (Password Protected) and Break Into Smaller Files
- Exfil Compressed Archive to FTP
- Exfil Compressed Archive to Dropbox
- Exfil Compressed Archive to GitHub Repositories | Gists
  - Additionally: Exfil Directory Files to Github
- Exfil Compressed Archive to S3 via AWS CLI
- Transfer Compressed Archive to Separate S3 Bucket via AWS CLI
- Scheduled Exfiltration (uses the standard HTTP C2 channel)

Note: the exfiltration abilities (to GitHub, Dropbox, FTP, and AWS) require a compressed archive with a corresponding
`host.dir.compress` fact unless otherwise noted.

If you want to skip straight to an example, [click here](#operation)

## Groundwork - Destinations
To fully capitalize on the exfiltration abilities, you will need to do a little set up on the far end to 
receive the exfiltrated data.

### Dropbox
If you do not have a Dropbox account already, you can obtain a free account (with storage size limitations) by navigating
to the [signup page for a basic account](https://dropbox.com/basic) and fill in the required information.

Once you have an activated account, you will navigate to the App Center and select 'Manage'. In the left-hand toolbar and
near the bottom, select 'Build an App'. The name will need to be unique; fill out the requested information. Generate
an access token and set it for the desired expiration time (default as of this document is 4 hours). You may need to
update your access token periodically prior to operations.

On the permissions tab, grant the application read and write access for files and folders, then submit the application.

Uploaded files should appear under Apps/AppName/FolderName if you elected to segregate app folders.

### GitHub Repositories
Chances are you already have a [GitHub account](https://github.com) if you're using this platform. 
Create a new repository per the standard instructions. If you do not already have a private access token, you can create
it under Settings > Developer Settings > Personal Access Tokens. Select if you want the token to also apply to Gists 
while you're here.

You can commit directly to main if desired, or you can use a branch for your operations (just be sure to update the fact
source with the desired branch, discussed below). Keep track of your GitHub username, access token, and branch name for 
the fact source.

### GitHub Gist
This is a much simpler case - simply have a GitHub account and obtain an access token as described above (Settings >
Developer Settings > Personal Access Tokens). Ensure the access token also applies to Gists if you already have one.

Keep track of the access token and your username for the fact source.

### FTP
There are a number of ways to start an FTP server depending on your OS; start the service per your operating system's 
requirements. As a note, FTP services may not like writable chroots if configured. To avoid this, either allow writeable
chroots or designate a specific folder for Caldera uploads and supply that in the fact source.

For example, with vsftpd you can either:

- Edit `/etc/vsftpd.conf` to include `allow_writable_chroot=YES`
- Supply a writable folder in addition to the FTP server address in the Caldera fact source. E.g. `value: 192.168.1.2/upload`

### AWS
The exfiltration via AWS CLI abilities assume the AWS CLI is installed on the host machine. For use with an IAM user,
the proper credentials (access key, secret access key, and also session token if using MFA) must be provided for the
`[default]` profile in `~/.aws/credentials`. The `[default]` profile may require some additional setup with the correct
region and output within `~/.aws/config`.

For exfiltration to S3 bucket, the permissions must be in place to allow the `[default]` profile read/write accesses
to the target S3 bucket (examples: `s3:ListBucket`, `s3:PutObject`).

For transferring data to a separate S3 bucket, proper policies must be configured in the source AWS account to allow
listing (`s3:ListBucket`) and getting (`s3:PutObject`) objects from the source S3 bucket in addition to listing,
putting objects, and setting the ACL when putting (`s3:PutObjectAcl`) an object to the destination S3 bucket. Policies
must also be configured in the destination AWS account to allow the source AWS account to put objects and set the
object's ACL in the destination S3 bucket. This will ensure that objects transferred to the destination account will
automatically become owned by the destination bucket owner, who will then have full control of the transferred objects.

## The Fact Source
Caldera uses **facts** in its operations to collect and act upon information of import. For more general information, 
see the [docs](https://caldera.readthedocs.io/en/latest/Basic-Usage.html#facts). To aid in exfiltration testing, Stockpile
contains a fact source for basic testing with the various facts consumed by the abilities listed above (data/sources/2ccb822c-088a-4664-8976-91be8879bc1d).
Note that this **does not** include all facts used by other exfiltration abilities in Caldera, such as those offered by
the Atomic plugin.

Most of the fact source is commented-out by default excepting the search and stage ability. To plan an operation,
first consider the various file searching and staging options available. The source file contains information on the 
options available to you as the user along with the required formatting and default values as examples.

Review the remaining facts and un-comment (remove the `#` at the start of the line) the applicable facts -- both the trait
and value lines. For sections like GitHub, notes have been left regarding which facts are required for either exfil to
repositories or Gists. For example, only the first two facts below need to be un-commented and updated if using Gists:
```
  # GitHub Exfiltration
  # -------------------------------------
  #- trait: github.user.name        <--- Uncomment
  #  value: CHANGEME-BOTH           <--- Uncomment & Update
  #- trait: github.access.token     <--- Uncomment
  #  value: CHANGEME-BOTH           <--- Uncomment & Update
  #- trait: github.repository.name
  #  value: CHANGEME-RepoOnly
  #- trait: github.repository.branch
  #  value: CHANGEME-RepoOnly
```

If you're planning a longer operation requiring other facts, feel free to add them to this file using the standard syntax.

## Adversaries

Before diving into an example, one last thing you should be aware of: pre-built adversaries. You may already be familiar
with adversaries like Hunter and Thief -- to give you a baseline, we've included four adversaries covering exfiltration
operations to Dropbox, FTP, and GitHub (1x Repository, 1x Gist). If you want to try them out quickly, simply create
the corresponding exfiltration destination account/service and run an operation as normal using 
Advanced Thief via \[ Dropbox | FTP | GitHub Repo | GitHub Gist \] and the provided fact source with appropriate entries.

These adversaries work nearly identically, first finding and staging files using Advanced File Search and Stager and
compressing the staged directory via utility with a password. Once converted to an archive, the last ability is exfil
to the selected destination.

## An Example

Let's walk through an example of exfiltrating a compressed archive to a GitHub repository. 

### Pre-Work: GitHub
First, ensure you have an account and that you have generated an access token as described above. In either the UI 
(github.com) or via the command line interface, create a repository to house the exfiltrated data. If desired, 
additionally create a branch. For this demo, we have selected 'caldera-exfil-test' as the repository and 'demo-op' as 
the branch. In the source file, edit the section marked for GitHub as follows. In the event you choose to use the main 
branch, supply that instead for the branch fact. 

```
id: 2ccb822c-088a-4664-8976-91be8879bc1d
name: Exfil Operation
...

  # GitHub Exfiltration
  # -------------------------------------
  - trait: github.user.name           # <--- Uncommented
    value: calderauser                # <--- Uncommented & Updated
  - trait: github.access.token        # <--- Uncommented
    value: ghp_dG90YWxseW1V1cG...     # <--- Uncommented & Updated
  - trait: github.repository.name     # <--- Uncommented
    value: caldera-exfil-test         # <--- Uncommented & Updated
  - trait: github.repository.branch   # <--- Uncommented
    value: demo-op                    # <--- Uncommented & Updated
...
```

### Operation Planning
With GitHub ready to go, it's time to consider other operational facts. For this example, we will focus on a quick
smash-and-grab without any other actions. Returning to the source file, let's look at the topic section for file search
and stage. While there are instructions in the file, we'll cover a little more detail here.

To summarize options, you can find files by: **extension** and **content** and cull the results by providing a variety
of limiters: **modified timeframe** (default: last 30 days) and/or **accessed timeframe** (default: last 30 days), only
searching certain directories (e.g. `c:\users` or `/home`) or explicitly excluding directories (e.g. any "Music" folders).
Additionally, for Windows targets you can exclude certain extensions. This is largely to exclude executables from capture
by the content search, which the Linux command can do inherently. The included source file has default values for many 
of these options but can easily be adjusted.

### Finding Content
Looking first at how to identify content we want, we'll discuss the extensions and content search. For extensions, you 
can control Windows and Linux separately to account for different important file types between the operating systems. For the 
extensions, you'll note instructions in the file regarding format. These extensions should be provided in a 
comma-separated list with no periods or asterisks as they are added in the payload. If you're not picky, you can also 
supply **all** or **none**.

The content search looks inside of files for the given string(s). This is shared between operating systems; simply include
your terms of import (spaces are ok!) in a comma-separated list. By default, Linux will ignore any binary files when
performing this search; Windows targets should use the excluded extensions list.

For this example, we'll leave the default values and be sure to exclude common binary files we might find from Windows.

```
...
  # ---- Comma-separated values, do not include '.' or '*', these are added in the payload if needed. Example: doc,docx
  # ---- May also use 'all' for INCLUDED extensions and 'none' for EXCLUDED extensions
  - trait: linux.included.extensions
    value: txt,cfg,conf,yml,doc,docx,xls,xlsx,pdf,sh,jpg,p7b,p7s,p7r,p12,pfx
  - trait: windows.included.extensions
    value: doc,xps,xls,ppt,pps,wps,wpd,ods,odt,lwp,jtd,pdf,zip,rar,docx,url,xlsx,pptx,ppsx,pst,ost,jpg,txt,lnk,p7b,p7s,p7r,p12,pfx
  - trait: windows.excluded.extensions # Mainly used to avoid binary files during content search, not needed for Linux
    value: exe,jar,dll,msi,bak,vmx,vmdx,vmdk,lck
    
  # ---- Comma-separated values to look for. Spaces are allowed in terms. May also use 'none'
  - trait: file.sensitive.content
    value: user,pass,username,password,uname,psw
...
```

### Limiting our results
With the content identified, we may want to focus our efforts on areas that might contain sensitive documents to save
time in the operation and post-processing. Adversaries have been observed using similar tactics, limiting results
to certain directories or documents seeing use in a given time period. As with the extensions and content, the provided 
source file has default values set, but they can easily be changed.

First, you can choose an information cutoff date. As with the extensions, you can specify 'none' if you do not wish to
limit the results. You can also pick one or the other (modified or accessed) if you only care about one metric. Simply
supply a negative integer value, which represents the number of past days from today to include. We'll leave it with 
the default here.

```
  # ---- Integer; cutoff for access/modification (-30 = accessed/modified in last 30 days)
  # ---- May also use 'none' for either or both options. Note on usage: if both options are present, the script
  # ---- uses a boolean "or" - if a file was accessed in the desired timeframe but not modified in the time frame,
  # ---- it will still be collected. If modification is more important, set accessed time to "none".
  - trait: file.last.accessed
    value: -30
  - trait: file.last.modified
    value: -30
```

Next, let's look at the directories. You can again supply comma-separated lists of directories or a single directory. These
items will be used as the root nodes for a recursive search within. The default is `c:\users` and `/home`, but we have
changed things up here to limit it to a folder containing test files.

```
  # ---- Comma-separated, full paths to base folders (will recurse inside)
  - trait: windows.included.directories
    value: c:\caldera-test-files
  - trait: linux.included.directories
    value: /caldera-test-files
```

If searching a directory like `c:\users` or `/home`, you will likely encounter folders you (or an attacker) do not much
care for. To address this, you can supply a comma-separated list of **phrases** to exclude from directory paths. These
**do not** need to be full paths and **can** include spaces. For the example below, we have excluded things like "Music"
and "saved games", folders found by default in user directories. Because these folders aren't likely in the test folder
we're using, these shouldn't be issues. Be sure to account for any folders that may contain information that would
violate your organization's policy if it were to be published to a site outside of organizational control.

```
  # ----  Comma-separated, does not need to be full paths. May also use 'none'
  - trait: windows.excluded.directories
    value: links,music,saved games,contacts,videos,source,onedrive
  - trait: linux.excluded.directories
    value: .local,.cache,lib
```

### Staging
Next up, we'll discuss staging. Because this file does search _and_ stage, users can specify where to move the files.
By default, Windows targets will stage to the user's recycle bin and Linux targets will stage to /tmp as both of these
locations should be writable by default. In each case, the ability will create a _hidden_ folder called "s" at these
locations.

If changing the default location, be sure to include a **full path**. Because the Recycle Bin requires some processing
to get the user's SID, you can instead use the string "Recycle Bin" which will be parsed into the correct location. As
noted in the instructions, if the staging directory is changed from the default, the ability does contain a fall-back
in the event the selected directory is not writable. These values are `c:\users\public` and `/tmp`.

```
  # Include the full path or use "Recycle Bin". Fall-back in the payload file is "c:\users\public".
  # Recycle Bin will attempt to create a staging folder at c:\$Recycle.Bin\{SID} which should be writable by default
  # Takes given location and creates a hidden folder called 's' at the location.
  - trait: windows.staging.location
    value: Recycle Bin

  # ---- Include the full path, ensure it's writable for the agent. Fallback is /tmp. Creates a hidden folder called .s
  - trait: linux.staging.location
    value: /tmp
```

To support safe testing, the ability additionally has a **safe mode** option. It is **disabled by default** and will
find all files matching the parameters set before. If this fact is changed to 'true', you can supply an identifying value
which indicates the file is for testing. This identifying value **must be at the end** of the file. The
default value is "_pseudo". If Safe Mode is enabled, Caldera **will not** stage any files that do not end in "_pseudo".

To provide a few examples, if safe mode is on with the value "_pseudo":

- `interesting_file.docx` -- matches the requested extension -- **will not be staged**
- `interesting_content.txt` -- matches the requested content -- **will not be staged**
- `interesting_pseudo_data.doc` -- matches the requested content -- **will not be staged** because "_pseudo" is in the wrong place
- `uninteresting_file_pseudo.random` -- doesn't match the requested extension -- **will not be staged** despite the "_pseudo"
- `interesting_file_pseudo.docx` -- matches the requested extension -- **will be staged**
- `interesting_content_pseudo.txt` -- that matches the requested content -- **will be staged**

```
  # ---- Safe Mode - Only stages files with the appropriate file ending if enabled (e.g. report_pseudo.docx)
  - trait: safe.mode.enabled
    value: false
  - trait: pseudo.data.identifier
    value: _pseudo
```

### Final Piece: A Password
For this demonstration, we will be using the password-protected archive ability added in this update. The source contains
a default value of C4ld3ra but can be changed to anything if more security is required (e.g., real files used in testing).
As noted in the source file, certain special characters may be escaped when inserted into the command. This may result
in a different password than what you entered - view the operation logs to see exactly what was used. You should still
be able to decrypt the archive, but will need to include any escape characters added during the operation. For example,
`Pa$$word` may have become `Pa\$\$word` or ```Pa`$`$word```.

```
  # Encrypted Compression
  # Note: For passwords with special characters like # and $, you may need to include escapes (\ or `)
  # when re-entering the password to decrypt the archive. Examine the operation output to see the exact password used.
  # If using special characters, put the password in 'single quotes' here to prevent parser errors.
  # -------------------------------------
  - trait: host.archive.password
    value: C4ld3ra
```

## Operation
Whew. Let's recap a few things. So far we have:
1. Set up a GitHub repository and branch to receive the exfiltrated files, using a personal access token
2. Updated the selected source file with the pertinent information about the GitHub account and ensured the lines are uncommented
3. Adjusted and reviewed the source file for the files we want to find and exclude, provided a staging location, and provided a password

With all of that in place, fire up Caldera as normal. For this demonstration, we'll use a pre-built adversary, but you
can easily add other abilities (even multi-exfil paths) to your own adversary or operation.

Navigate to the Operations tab and hit "Create an Operation". Fill in the name, select "Advanced Thief via GitHub Repo"
as the adversary, and finally select the source file ("Exfil Operation" if using the supplied file) containing the facts
we set up earlier. Adjust any settings under Advanced if desired, otherwise start the operation. The agent should
collect the requested files in the staging directory, compress them, and POST the files to the desired repository/branch.
The filename will be a timestamp (YYYYMMDDHHmmss), exfil, the agent's paw, and the original file name.

In our demonstration, refreshing the repository shows the following: 20211112094022-exfil-gwsnys-s.tar.gz.gpg. This
file could then be downloaded an decrypted with the default password.

Operation cleanup should remove the compressed archive and the staging directory (+ contents). This cleanup does not occur until the operation is terminated, so you could add another exfiltration (e.g. to Dropbox) in the interim.

## Wrap-up
That about does it! If you have any questions, please reach out to the team on Slack.
