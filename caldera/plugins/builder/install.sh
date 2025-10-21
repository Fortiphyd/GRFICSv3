#!/bin/bash

USER=$(printf '%s\n' "${SUDO_USER:-$USER}")
CRITICAL=1
WARNING=0
CRITICAL_FAIL=0
WARNING_FAIL=0

function installed() {
    echo "[+] $1 installed"
    echo "[+] $1 installed">>install_log.txt
}

function failed() {
    echo "[x] "$1" FAILED to install"
    echo "[x] "$1" FAILED to install">>install_log.txt
    echo " - command: $2">>install_log.txt
}

function install_wrapper() {
    echo "[-] $1"
    if eval $2; then
        installed "$1"
    else
        failed "$1" "$2"
        if [[ $3 == 1 ]]; then
            CRITICAL_FAIL=1
        else
            WARNING_FAIL=1
        fi
    fi
}

function initialize_log() {
    echo "Docker install log">install_log.txt
}

function ubuntu_install_docker() {
    install_wrapper "Remove existing docker stubs" "apt-get remove -y docker docker-engine docker.io containerd runc" $WARNING
    install_wrapper "Install pre-requisites" "apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common" $WARNING
    install_wrapper "Add docker GPG key" "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -" $WARNING
    install_wrapper "Add docker repository" "add-apt-repository 'deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable'" $WARNING
    install_wrapper "Install docker" "apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io" $WARNING
    install_wrapper "Add user to docker group" "usermod $USER -a -G docker" $CRITICAL
    exec sudo su -l $USER
}

function darwin() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[X] Not implemented at this time..."1
}

function ubuntu() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[-] Installing on Ubuntu (Debian)..."
    initialize_log
    ubuntu_install_docker
}

function kali() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[-] Installing on Kali (Debian)..."
    initialize_log
    ubuntu_install_docker
}

function centos() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[X] Not implemented at this time..."1
}

if [[ "$(uname)" == *"Darwin"* ]]; then
  darwin
elif [[ "$(lsb_release -d)" == *"Ubuntu"* ]]; then
  ubuntu
elif [[ "$(cat /etc/centos-release 2>/dev/null)" == *"CentOS"* ]]; then
  centos
elif [[ "$(lsb_release -d)" == *"Fedora"* ]]; then
  centos
elif [[ "$(lsb_release -d)" == *"Kali"* ]]; then
  kali
else
    echo "OS not supported. Supported OS are Ubuntu, Centos, Fedora and Kali." && exit 1
fi
