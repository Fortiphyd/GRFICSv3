# MITRE Caldera Plugin: Emu

A plugin supplying Caldera with TTPs from the Center for Threat Informed Defense (CTID) Adversary Emulation Plans.

# Installation

Using the Emu plugin with Caldera will enable users to access the adversary profiles contained in the [CTID Adversary Emulation Library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library). 

To run Caldera along with the Emu plugin:
1. Download Caldera as detailed in the [Installation Guide](https://github.com/mitre/Caldera)
2. Enable the Emu plugin by adding `- emu` to the list of enabled plugins in `conf/local.yml` or `conf/default.yml` (if running Caldera in insecure mode)
3. Start Caldera to automatically download the Adversary Emulation Library to the `data` folder of the Emu plugin. 
4. Stop Caldera. 
5. Some adversaries may require additional payloads and executables to be downloaded. Run the `download_payloads.sh` script to download these binaries to the `payloads` directory.
6. Start Caldera again. You will see the Emu plugin shown on the left sidebar of the Caldera server, and you will be able to access the Adversary Emulation Library adversary profiles from the Adversary tab of the Caldera server.

# Additional setup
Each emulation plan will have an adversary and a set of facts. Please ensure to select the related facts to the 
adversary when starting an operation. 

Because some payloads within the Adversary Emulation Library are encrypted, a Python script is used to automate
the decryption which requires installation of some dependencies. Depending on the host OS, `pyminizip`
can be installed using the following:

- Ubuntu: `apt-get install zlib1g`
- MacOS: `brew install zlib`
- All OS's: `pip3 install -r requirements.txt`

See URL for more information regarding `pyminizip`: https://github.com/smihica/pyminizip

## Acknowledgements

- [Adversary Emulation Library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library)
