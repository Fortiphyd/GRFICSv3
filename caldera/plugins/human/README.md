# MITRE Caldera Plugin: Human

Plugin supplying Caldera with human emulation capabilities.

## Overview

The Human plugin allows you to build “humans” that will perform user actions on a target system as a means to obfuscate red actions by Caldera. Each human is built for a specific operating system and leverages the Chrome browser along with other native OS applications to perform a variety of tasks. Additionally, these humans can have various aspects of their behavior “tuned” to add randomization to the behaviors on the target system.

## Requirements

### Caldera Server
On the Caldera server, there are additional python packages required to use the Human plugin. These python packages can be installed by navigating to the plugins/human/directory and running the command `pip3 install -r requirements.txt`.

### Target Machine 
* Linux, MacOS, or Windows (with Powershell)
* Python3
* Python package `virtualenv`
* Google Chrome

## Further Reading
*   [Step by step instructions for setting up & using the Human Plugin](https://github.com/mitre/human/wiki)

*   [Read more about the Human Plugin](https://caldera.readthedocs.io/en/latest/Plugin-library.html?#human)
