# GRFICSv3
Cyberphysical simulation of a chemical plant

![Chemical plant screenshot](/images/tanks.png)

# Installation

## Installing Docker

GRFICS uses Docker and Docker Compose. For a more efficient, lighter-weight installation, use Linux (either VM or WSL). There is currently a known issue with Docker Desktop on Windows that we are working on resolving, so it is not recommended at this time.

On Linux, run the following commands
```
sudo apt-get install docker git git-lfs
```

## Installing GRFICS

First, clone this repo.
```
git clone https://github.com/Fortiphyd/GRFICSv3
```


In the command line, change directories to the top-level directory of the cloned repo. Now run

```
cd GRFICSv3
docker compose build
```

and then run

```
docker compose up
```

If building fails with a message about being unable to create a network interface, edit docker-compose.yml lines 140 and 149 to match the name of your network interface.

Open a web browser and visit localhost. If GRFICS is built correctly, you should see a visualization of a chemical plant.

# Using GRFICS
## Starting and stopping the environment
If you are using Docker Desktop, you can use the GUI as you would any other Docker program, clicking stop and play on individual containers, or on the overall container. If you are using the command line, you can use the standard Docker commands, such as
```
docker stop $(docker ps -q)
```
to stop all running containers

## Containers
 - Simulation: Accessible in your browser at localhost
   
   ![Simulation screenshot](/images/sim.png)
 - Kali: Accessible over noVNC in your browser at localhost:6088/vnc.html, with credentials kali:kali
   
   ![Kali screenshot](/images/kali.png)
 - Caldera: Accessible in your browser at localhost:8888, with credentials red:fortiphyd-red
   
   ![Caldera screenshot](/images/caldera.png)
 - Engineering Workstation: Accessible over noVNC in your browser at localhost:6080/vnc.html
   
 ![EW screenshot](/images/ew.png)
 - Router: Accessible from inside either simulated network at 192.168.90.200:5000 or 192.168.95.200:5000 with credentials admin:password
   
   ![Router screenshot](/images/firewall.png)
 - PLC: Accessible in your browser at localhost:8080 or in the network at 192.168.95.2:8080 with credentials openplc:openplc
   
   ![PLC screenshot](/images/plc.png)
 - HMI: Accessible in your browser at localhost:6081 or in the network at 192.168.90.107:8080 with credentials admin:admin
   
   ![HMI screenshot](/images/hmi.png)

## Connecting to containers
In Docker Desktop, each container will have a link that you can click on to connect to that container. The simulation VM link will display the 3d graphical model of the chemical plant. The PLC and HMI link will lead to a login page to those devices.

The attacker and engineering workstation VM link will lead to an index page. Click on the vnc link from there to connect to that container over VNC.
