# We are not able to bundle some payloads because their licensing
# prohibits redistribution (notably sysinternals).  This script will
# will download non-redistributable payloads.  If you're deploying
# the plugin without internet access, you can copy this script to
# an internet connected host, run it, and then copy the resulting
# payloads back to the emu/payloads directory

curl -o payloads/AdFind.zip http://www.joeware.net/downloads/files/AdFind.zip
unzip -P $(unzip -p payloads/AdFind.zip password.txt) payloads/AdFind.zip -d payloads/
cp payloads/AdFind.exe payloads/adfind.exe

curl -o payloads/dnscat2.ps1 https://raw.githubusercontent.com/lukebaggett/dnscat2-powershell/master/dnscat2.ps1

curl -o payloads/NetSess.zip http://www.joeware.net/downloads/files/NetSess.zip
unzip payloads/NetSess.zip -d payloads/
cp payloads/NetSess.exe payloads/netsess.exe

curl -o payloads/nbtscan.exe http://unixwiz.net/tools/nbtscan-1.0.35.exe

curl -o payloads/psexec.exe https://github.com/ropnop/impacket_static_binaries/releases/download/0.9.22.dev-binaries/psexec_windows.exe
cp payloads/psexec.exe payloads/PsExec.exe

curl -o payloads/putty.exe https://the.earth.li/~sgtatham/putty/latest/w64/putty.exe

curl -o payloads/secretsdump.exe https://github.com/ropnop/impacket_static_binaries/releases/download/0.9.22.dev-binaries/secretsdump_windows.exe

curl -o payloads/tcping.exe https://download.elifulkerson.com//files/tcping/0.39/tcping.exe

curl -o payloads/wce_v1_41beta_universal.zip https://www.ampliasecurity.com/research/wce_v1_41beta_universal.zip
unzip payloads/wce_v1_41beta_universal.zip -d payloads/

curl -o payloads/wmiexec.vbs https://raw.githubusercontent.com/Twi1ight/AD-Pentest-Script/master/wmiexec.vbs

curl -o payloads/psexec_sandworm.py https://raw.githubusercontent.com/SecureAuthCorp/impacket/c328de825265df12ced44d14b36c688cd9973f5c/examples/psexec.py

curl -o payloads/PSTools.zip https://web.archive.org/web/20221102141531/http://download.sysinternals.com/files/PSTools.zip
unzip payloads/PSTools.zip -d payloads/PSTools
psexec_md5=$(md5sum payloads/PSTools/PsExec64.exe | awk '{ print $1 }')
if [ "$psexec_md5" = "84858ca42dc54947eea910e8fab5f668" ]
then
    target_dir="data/adversary-emulation-plans/turla/Resources/payloads/snake"
    mkdir -p "$target_dir" && cp payloads/PSTools/PsExec64.exe $target_dir/PsExec.exe
    echo "PsExec64.exe v2.4 copied to Turla payloads directory"
else
    echo "PsExec from PSTools.zip with MD5 '$psexec_md5' does not match v2.4 with MD5 of 84858ca42dc54947eea910e8fab5f668"
fi

curl -o payloads/pscp.exe https://the.earth.li/~sgtatham/putty/latest/w64/pscp.exe
target_dir="data/adversary-emulation-plans/turla/Resources/payloads/carbon"
mkdir -p "$target_dir" && cp payloads/pscp.exe $target_dir/pscp.exe
echo "Pscp.exe copied to Turla payloads directory"

curl -o payloads/plink.exe https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe
target_dir="data/adversary-emulation-plans/turla/Resources/payloads/carbon"
mkdir -p "$target_dir" && cp payloads/plink.exe $target_dir/plink.exe
echo "Plink.exe copied to Turla payloads directory"

curl -o payloads/m64.exe https://github.com/ParrotSec/mimikatz/blob/master/x64/mimikatz.exe
echo "x64 mimikatz.exe copied to payloads directory as m64.exe"