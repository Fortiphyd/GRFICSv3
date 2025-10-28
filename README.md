# GRFICSv3
Cyberphysical simulation of a chemical plant

# Installation

## Installing Docker

GRFICS uses Docker and Docker Compose. We recommend installing Docker Desktop, which includes the Docker engine as well as Docker Compose.

https://docs.docker.com/compose/install/

## Installing GRFICS
First, clone this repo.

In Windows, if the Docker engine is not already running, start the Docker Desktop application using the Start menu.

In the command line, change directories to the top-level directory of the cloned repo. Now run

```
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

## Connecting to containers
In Docker Desktop, each container will have a link that you can click on to connect to that container. The simulation VM link will display the 3d graphical model of the chemical plant. The PLC and HMI link will lead to a login page to those devices.

The attacker and engineering workstation VM link will lead to an index page. Click on the vnc link from there to connect to that container over VNC.
