#!/bin/bash

# Default values
extensionsIn="txt,cfg,conf,yml,doc,docx,xls,xlsx,pdf,sh,jpg"
accessDate="-30"
modifyDate="-30"
stagingDirectory="/tmp"
directoriesIn="/home"
sensitiveWordsIn="user,username,pass,password,authorized_keys,ssh-rsa"
excludeDirIn=".local,.cache,lib,caldera"
safeMode=false
pseudoExt="_pseudo"

while [[ $# -gt 0 ]]
do
	case $1 in
		-e|--extensions)
			extensionsIn=$2
			shift 2
			;;
		-d|--directories)
			directoriesIn=$2
			shift 2
			;;
		-x|--exclude-dir)
			excludeDirIn=$2
			shift 2;;
		-s|--search-strings)
			sensitiveWordsIn=$2
			shift 2
			;;
		-a|--accessed)
			accessDate=$2
			shift 2
			;;
		-m|--modified)
			modifyDate=$2
			shift 2
			;;
		-o|--staging-directory)
			stagingDirectory=$2
			shift 2
			;;
	  --safe-mode)
	    safeMode=$(echo $2 | tr '[:upper:]' '[:lower:]')
	    shift 2
	    ;;
	  -p|--pseudo-ext)
	    pseudoExt=$2
	    shift 2
	    ;;
		-*|--*=)
			echo "Error: unsupported flag $1" >&2
			exit 1;
	esac
done

if [ -w $stagingDirectory ]; then
	stagingDirectory=$stagingDirectory/.s
else
	stagingDirectory="/tmp/.s"
fi

################
# FIND COMMAND #
################
findCMD="find"

extensionsIn="$(echo "${extensionsIn}" | /bin/tr -d '[:space:]')"
directoriesIn="$(echo "${directoriesIn}" | /bin/tr -d '[:space:]')"
IFS=',' read -r -a extArray  <<< "$extensionsIn"
IFS=',' read -r -a dirArray <<< "$directoriesIn"
IFS=',' read -r -a excludeDirArray <<< "$excludeDirIn"

# Directories to search
for dir in "${dirArray[@]}"
do
	findCMD="$findCMD $dir"
done

# Excluded Directories
if [[ $(echo "${excludeDirArray[0]}" | /bin/tr [A-Z] [a-z]) != "none" ]]; then
  findCMD="$findCMD \\( -name \"*${excludeDirArray[0]}*\""
	for p in "${excludeDirArray[@]:1}"
	do
		findCMD="$findCMD -o -name \"*$p*\""
	done
  findCMD="$findCMD \\) -prune -false -o"
fi

# Extensions to search
if [[ $(echo "${extArray[0]}" | /bin/tr [A-Z] [a-z]) == "all" ]]; then
	findCMD="$findCMD \\( -iname \"*.*\""
else
	findCMD="$findCMD \\( -iname \"*.${extArray[0]}\""
	for ext in "${extArray[@]:1}"
	do
		findCMD="$findCMD -o -iname \"*.$ext\""
	done
fi
findCMD="$findCMD \\)"

# Access and Modify Dates
if [[ ${accessDate,,} != "none" ]]; then
	findCMD="$findCMD -a \\( -atime $accessDate"
	if [[ ${modifyDate,,} != "none" ]]; then
		findCMD="$findCMD -o -mtime $modifyDate"
	fi
	findCMD="$findCMD \\)"
elif [[ ${modifyDate,,} != "none" ]]; then
	findCMD="$findCMD -a \\( -mtime $modifyDate \\)"
fi

# Safe mode
if $safeMode; then
  findCMD="$findCMD -a -name \"*$pseudoExt.*\""
fi

findCMD="$findCMD -exec cp -t $stagingDirectory {} + 2>/dev/null"

mkdir -p $stagingDirectory
echo $findCMD | /bin/bash

################
# GREP COMMAND #
################

# Skip grep entirely if no search strings were provided -- "none"
if [[ ${sensitiveWordsIn,,} != "none" ]]; then
	grepCMD="grep"

	# Excluded directories, if applicable
	if [[ ${excludeDirArray[0],,} != "none" ]]; then
		exDirGlob="--exclude-dir={*${excludeDirArray[0]}*"
		for d in "${excludeDirArray[@]:1}"
		do
			exDirGlob="$exDirGlob,*$d*"
		done
		grepCMD="$grepCMD $exDirGlob}"
	fi

	grepCMD="$grepCMD -iIErl '"

	IFS=',' read -r -a sensArray  <<< "$sensitiveWordsIn"

	grepCMD="$grepCMD${sensArray[0]}"

	for item in "${sensArray[@]:1}"
	do
		grepCMD="$grepCMD|$item"
	done

	grepCMD="$grepCMD'"
	for dir in "${dirArray[@]}"
	do
		grepCMD="$grepCMD $dir"
	done

	echo $grepCMD | /bin/bash 2>/dev/null | while read line; do
		if $safeMode; then
			if echo $line | grep -q "$pseudoExt"; then
				cp $line $stagingDirectory 2>/dev/null
			fi
		else
			cp $line $stagingDirectory 2>/dev/null
		fi
	done
fi

echo $stagingDirectory