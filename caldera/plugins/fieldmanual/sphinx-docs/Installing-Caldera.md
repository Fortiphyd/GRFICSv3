# Installing MITRE Caldera

Caldera can be installed in four commands using the [concise installation instructions](#concise) and, optionally, be installed and run using a [docker container](#docker-deployment).

## Requirements

Caldera aims to support a wide range of target systems, the core requirements are listed below:

* Linux or MacOS operating system
* Python 3.8 or later (with pip3)
* NodeJS v16 or later (for Caldera v5)
* A modern browser (Google Chrome is recommended)
* The packages listed in the [requirements file](https://github.com/mitre/caldera/blob/master/requirements.txt)

### Recommended

To set up a development environment for Caldera, and to dynamically compile agents, the following is recommended:

* GoLang 1.17+ (for optimal agent functionality)
* Hardware: 8GB+ RAM and 2+ CPUs
* The packages listed in the [dev requirements file](https://github.com/mitre/caldera/blob/master/requirements-dev.txt)

## Installation

### Concise

Caldera can be installed quickly by executing the following 4 commands in your terminal.

```sh
git clone https://github.com/mitre/caldera.git --recursive
cd caldera
pip3 install -r requirements.txt
python3 server.py --insecure --build
```

### Step-by-step Explanation

Start by cloning the Caldera repository recursively, pulling all available plugins. It is recommended to pass the desired [version/release](https://github.com/mitre/caldera/releases) (should be in x.x.x format). Cloning any non-release branch, including master, may result in bugs.

In general, the `git clone` command takes the form:

```sh
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x
```

To install version 5.0.0, one would execute:

```sh
git clone https://github.com/mitre/caldera.git --recursive --branch 5.0.0
```

Once the clone completes, we can jump in to the new `caldera` directory:

```sh
cd caldera
```

Next, install the pip requirements:

```sh
sudo pip3 install -r requirements.txt
```

Finally, start the server (optionally with startup [flags](Server-Configuration.md#startup-parameters) for additional logging):

```sh
python3 server.py --build
```

The `--build` argument is only required on the first boot of the Caldera server, or when latest changes are pulled.

Once started, log in to http://localhost:8888 with the `red` using the password found in the `conf/local.yml` file (this file will be generated on server start).

To learn how to use Caldera, navigate to the Training plugin and complete the capture-the-flag style course.

## Docker Deployment

Caldera can be installed and run in a Docker container.

Start by cloning the Caldera repository recursively, passing the desired version/release in x.x.x format:

```sh
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x
```

Next, build the docker image, changing the image tag as desired.

```sh
cd caldera
docker build --build-arg WIN_BUILD=true . -t caldera:server
```

Alternatively, you can use the `docker-compose.yml` file by running:

```sh
docker-compose build
```

Finally, run the docker Caldera server, changing port forwarding as required.  More information on Caldera's configuration is [available here](Server-Configuration.md#configuration-file).

```sh
docker run -p 7010:7010 -p 7011:7011/udp -p 7012:7012 -p 8888:8888 caldera:server
```

To gracefully terminate your docker container, do the following:

```
# Find the container ID for your docker container running Caldera
docker ps

# Send interrupt signal, e.g. "docker kill --signal=SIGINT 5b9220dd9c0f"
docker kill --signal=SIGINT [container ID]
```

## Offline Installation

It is possible to use pip to install Caldera on a server without internet access. Dependencies will be downloaded to a machine with internet access, then copied to the offline server and installed.

To minimize issues with this approach, the internet machine's platform and Python version should match the offline server. For example, if the offline server runs Python 3.8 on Ubuntu 20.04, then the machine with internet access should run Python 3.8 and Ubuntu 20.04.

Run the following commands on the machine with internet access. These commands will clone the Caldera repository recursively (passing the desired version/release in x.x.x format) and download the dependencies using pip:

```sh
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x
mkdir caldera/python_deps
pip3 download -r caldera/requirements.txt --dest caldera/python_deps
```

The `caldera` directory now needs to be copied to the offline server (via `scp`, sneakernet, etc).

On the offline server, the dependencies can then be installed with `pip3`:

```sh
pip3 install -r caldera/requirements.txt --no-index --find-links caldera/python_deps
```

Caldera can then be started as usual on the offline server:

```sh
cd caldera
python3 server.py --build
```
