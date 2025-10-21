# Powershell script to emulate typical system administrator tasks on an enterprise
# Run this anywhere you want to emulate an adversary presence

# BaseTask Object Structure
$BaseTaskClass = New-Object psobject -Property @{
    id   = $null
    task = $null
}

# BaseTask constructor
function BaseTask {
    param(
        [Parameter(Mandatory=$true)][Int]$id,
        [Parameter(Mandatory=$true)][String]$task
    )
    $basetask = $BaseTaskClass.psobject.copy()
    $basetask.id   = $id
    $basetask.task = $task
    $basetask
}

# BaseTask Execute task function
$BaseTaskClass | Add-Member -MemberType ScriptMethod -Name Execute -value {
    Invoke-Expression $this.task
}

# Event loop that selects random tasks to execute over a time interval
function eventloop{
    Param(
        [Parameter(Mandatory=$true)][System.Collections.ArrayList]$taskObjs
    )
     # Enter randomized task loop
    $minSleep = 10  # 10 seconds
    $maxSleep = 900 # 15 minutes
    while($true) {
        $index = Get-Random -Maximum $taskObjs.Count
        $taskObjs[$index].Execute()
        $sleep = Get-Random -Minimum $minSleep -Maximum $maxSleep
        Write-Host "Sleeping for"$sleep" seconds"
        Start-Sleep -s $sleep
    }
}

# Main
function main{
    Write-Host "+-------------------------------------------------+"
    Write-Host "|                                                 |"
    Write-Host "|---------- Emulating and Administrator ----------|"
    Write-Host "|                                                 |"
    Write-Host "+-------------------------------------------------+"
    $tasks =
        "Get-Process -Verbose",
        "Get-Service -Verbose",
        "Get-ComputerInfo",
        "Get-PSDrive",
        "Get-Command -Name Test-Connection -Syntax",
        "Get-LocalUser",
        "Get-WmiObject -Class Win32_Printer",
        "(New-Object -ComObject WScript.Network).EnumPrinterConnections()",
        "Get-Command -Noun Item",
        "New-Item -Path $HOME\MyImportantWork -ItemType Directory -Force`; Get-DnsClient | Out-File -FilePath $HOME\MyImportantWork\DNSinfo.txt -Force",
        "Get-Host",
        "Get-EventLog -Log `"Application`" | Out-File -FilePath $HOME\ApplicationLogsForWork.log -Force",
        "Get-ChildItem",
        "Get-History"

    # Array to store task object
    $taskObjs = [System.Collections.ArrayList]::new()

    # Construct task objects
    for($i=0;$i -lt $tasks.length;$i++){
        $taskObj = BaseTask -id $i -task $tasks[$i]
        $taskObjs.Add($taskObj) > $null
    }

    # Enter randomized task loop
    eventloop($taskObjs)
}

# Call Main to load script
main
