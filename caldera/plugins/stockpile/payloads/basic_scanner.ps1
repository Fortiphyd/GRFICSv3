function PrefixLength-ToAddrInt {
    param ([Parameter(Mandatory=$true)][int]$prefixLength);
    ([Math]::Pow(2, $prefixLength) - 1) * [Math]::Pow(2, 32 - $prefixLength);
};
function IPv4-ToInt {
    param ([Parameter(Mandatory=$true)][string]$ipv4);
    $octets = $ipv4 -split "\." | %{ [int]$_ };
    $result = ($octets[0]*[Math]::Pow(256,3)) + ($octets[1]*[Math]::Pow(256,2)) + ($octets[2]*256) + $octets[3];
    [uint32]$result;
};
function Int-ToIPv4 {
    param ([Parameter(Mandatory=$true)][uint32]$ipv4int);
    $octets = @();
    $remainder = $ipv4int;
    3..0 | %{
        $divideBy = [uint32]([Math]::Pow(256, $_));
        $octet = [Math]::Floor($remainder / $divideBy);
        $octets += [string]$octet;
        $remainder = $remainder % $divideBy;
    };
    $octets -join '.';
};
function Get-NetAddrInt {
    param (
        [Parameter(Mandatory=$true)][string]$ipv4,
        [Parameter(Mandatory=$true)][int]$prefixLength
    );
    $maskInt = PrefixLength-ToAddrInt $prefixLength;
    $ipv4int = IPv4-ToInt $ipv4;
    [uint32]($maskInt -band $ipv4Int);
};
function Scan-Netrange {
    param (
        [Parameter(Mandatory=$true)][string]$ipv4,
        [Parameter(Mandatory=$true)][int]$prefixLength,
        [Parameter(Mandatory=$true)][int[]]$ports
    );
    $netAddrInt = Get-NetAddrInt -ipv4 $ipv4 -prefixLength $prefixLength;
    $addrCount = [int]([Math]::Pow(2, 32 - $prefixLength)) - 1; # ignore the network address
    1..$addrCount | %{
        $ipv4 = Int-ToIpv4 ($netAddrInt + $_);
        $ports | %{
            $socket = new-object system.net.sockets.tcpclient;
            try {
                $Connection = $socket.beginconnect($ipv4, $_, $null, $null);
                if ($Connection) {
                    $Connection.AsyncWaitHandle.waitOne(50,$false) | out-null;
                    if ($socket.connected -eq $true) { echo "$ipv4 port $_ is open!"};
                };
            } catch {
            } finally {
                $socket.Close | Out-Null;
            };
        };
    };
};
function Ping-IPv4Network {
	param (
		[Parameter(Mandatory=$true)][string]$ipv4,
        [Parameter(Mandatory=$true)][int]$prefixLength
	);
	$timeout = 500;
	$minPerThread = 16;
	Get-Job | Remove-Job;
	$netAddrInt = Get-NetAddrInt -ipv4 $ipv4 -prefixLength $prefixLength;
	$addrCount = [int]([Math]::Pow(2, 32 - $prefixLength)) - 1;
	$numThreads = 4;
	if (($minPerThread * $numThreads) -gt $addrCount) {
		$numThreads = [math]::ceiling($addrCount / $minPerThread);
	};
	$perThread = [math]::ceiling($addrCount / $numThreads);
	$remaining = $addrCount;
	0..($numThreads - 1) | %{
		$currStartAddrInt = [uint32]($netAddrInt + ($_ * $perThread));
		$toDo = $perThread;
		if ($remaining -lt $perThread) { $toDo = $remaining; };
		Start-Job -ScriptBlock {
			param([uint32] $startAddrInt, [int] $toDo, [int] $timeout );
			function Int-ToIPv4 {
				param ([Parameter(Mandatory=$true)][uint32]$ipv4int);
				$octets = @();
				$remainder = $ipv4int;
				3..0 | %{
					$divideBy = [uint32]([Math]::Pow(256, $_));
					$octet = [Math]::Floor($remainder / $divideBy);
					$octets += [string]$octet;
					$remainder = $remainder % $divideBy;
				};
				$octets -join '.';
			};
			0..($toDo-1) | %{
				$currIP = Int-ToIpv4 ($startAddrInt + $_);
				$filter = 'Address="{0}" and Timeout={1}' -f $currIP, $timeout;
				$result = Get-WmiObject -Class Win32_PingStatus -Filter $filter |  Select-Object StatusCode;
				if ($result.StatusCode -eq 0) {
					echo $currIP;
				};
			};
		} -ArgumentList $currStartAddrInt, $toDo, $timeout | Out-Null;
		$remaining -= $toDo;
	};
	Get-Job | Wait-Job | Receive-Job;
};
