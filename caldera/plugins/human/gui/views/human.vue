<script setup>
import { inject, ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";

const $api = inject("$api");

onMounted(async () => {});
</script>

<style scoped>
.section-profile ul {
  list-style-type: none;
}

.section-profile li {
  text-align: left;
}

.row {
  text-align: center;
  padding: 25px;
  border-radius: 25px;
  width: 95%;
  display: flex;
  position: relative;
  border: 2px solid var(--navbar-color);
}

.transparent-row {
  margin-top: 50px;
  text-align: center;
  background-color: transparent;
  background-size: cover;
  padding: 25px;
  width: 95%;
  display: flex;
  position: relative;
}

.inner-row {
  border: none;
}

.row-simple {
  width: 95%;
  display: flex;
  position: relative;
}

.column {
  flex: 50%;
  color: var(--font-color);
  margin: 30px;
  max-width: 100%;
}
:root {
  --default-font: "Veranda", sans-serif;
  --theme-color: white;
  --primary-background: black;
  --secondary-background: #1e1e1e;
  --section-background: #1e1e1e;
  --font-color: white;
  --invert-percentage: 100%;
  --secondary-font-color: firebrick;
}

.row .row-interior {
  margin: 0;
  padding: 0;
  border: none;
  background: none;
}
.column .column-interior {
  background-color: black;
  padding: 25px;
  border-radius: 25px;
  margin-bottom: 0;
  margin-top: 0;
}

.human-box h4 {
  font-size: 20px;
  text-align: left;
}

.human-basic hr {
  opacity: 0.25;
}

.human-box hr {
  margin: 30px 0;
}

.human-box table {
  width: 100%;
}

.human-box table p {
  font-family: var(--default-font);
  font-size: 14px;
  font-weight: 700;
}
.human-box input[type="text"] {
  width: 100%;
  margin-top: 0;
}
.human-box select {
  width: 100%;
}

.human-box ul {
  padding-inline-start: 20px;
}
.human-box input[type="number"] {
  position: relative;
  width: 50px;
  padding: 0;
  margin: 0;
}

.human-box input[type="range"] ::before {
  display: none;
}

.human-header-list {
  list-style-position: inside;
  text-align: center;
  display: inline-block;
}
.install-container {
  position: relative;
}
.install-container .background-text {
  position: absolute;
  color: #f1f1f1;
  font-size: 40px;
  bottom: 10px;
  opacity: 30%;
}

.install-container span {
  font-size: 14px;
  line-height: 22px;
}

.duk-table-icon img {
  margin: 0;
}

#command-button {
  display: inline-block;
  background-color: black;
  color: var(--font-color);
  height: 25px;
  width: 50%;
  border: none;
  margin: 5px;
  cursor: pointer;
}

.delete-command {
  flex: 10%;
  color: red;
  cursor: pointer;
  font-size: 22px;
}
</style>

<script>
import { toast } from "bulma-toast";

export default {
  inject: ["$api"],
  data() {
    return {
      workflows: null,
      selectedWorkflows: [],
      commands: [],
      humans: [],
      selectedHuman: -1,
      humanName: "",
      selectedPlatform: "",
      serverIp: "",
      sleepInterval: 10,
      clusterSleepInterval: 500,
      tasksPerCluster: 5,
      commandBlock: "",
    };
  },
  created() {
    this.initHuman();
  },
  watch: {
    selectedHuman: "renderCommandBlock",
    serverIp: "renderCommandBlock",
  },
  methods: {
    initHuman() {
      this.serverIp = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;

      this.$api
        .get("/plugin/human/workflows")
        .then((workflows) => {
          this.workflows = workflows.data;
          return this.$api.get("/plugin/human/humans");
        })
        .then((humans) => {
          this.humans = humans.data;
        })
        .catch((error) => {
          console.error(error);
          toast({
            message: "Error loading workflows",
            position: "bottom-right",
            type: "is-warning",
            dismissible: true,
            pauseOnHover: true,
            duration: 2000,
          });
        });
    },
    generateHuman2() {
      if (!this.humanName) {
        toast({
          message: "Please enter a name for the human",
          position: "bottom-right",
          type: "is-warning",
          dismissible: true,
          pauseOnHover: true,
          duration: 2000,
        });
        return;
      }

      const validPlatforms = ["linux", "windows-psh", "darwin"];
      if (!validPlatforms.includes(this.selectedPlatform)) {
        toast({
          message: "Please select a valid platform",
          position: "bottom-right",
          type: "is-warning",
          dismissible: true,
          pauseOnHover: true,
          duration: 2000,
        });
        return;
      }

      if (this.selectedWorkflows.length === 0) {
        toast({
          message: "Please select at least one workflow",
          position: "bottom-right",
          type: "is-warning",
          dismissible: true,
          pauseOnHover: true,
          duration: 2000,
        });
        return;
      }

      const payload = {
        index: "build_human",
        platform: this.selectedPlatform,
        name: this.humanName,
        task_cluster_interval: this.clusterSleepInterval,
        task_interval: this.sleepInterval,
        task_count: this.tasksPerCluster,
        tasks: this.selectedWorkflows,
        extra: this.commands,
      };

      this.$api
        .post("/plugin/human/api", payload)
        .then((response) => {
          this.humans.push(response.data);
          this.selectedHuman = this.humans.length - 1;
          this.humanName = "";
          this.selectedPlatform = "";
          this.selectedWorkflows = [];
          this.commands = [];
          toast({
            message: "Human created",
            position: "bottom-right",
            type: "is-success",
            dismissible: true,
            pauseOnHover: true,
            duration: 2000,
          });
        })
        .catch((error) => {
          console.error(error);
          toast({
            message: "Error creating human",
            position: "bottom-right",
            type: "is-warning",
            dismissible: true,
            pauseOnHover: true,
            duration: 2000,
          });
        });
    },
    copyCommand() {
      navigator.clipboard.writeText(this.commandBlock).then(() => {
        toast({
          message: "Copied to clipboard",
          position: "bottom-right",
          type: "is-success",
          dismissible: true,
          pauseOnHover: true,
          duration: 2000,
        });
      });
    },
    renderCommandBlock() {
      if (!this.humans[this.selectedHuman]) {
        this.commandBlock = ``;
        return;
      }
      const extra = this.formatExtra(
        this.humans[this.selectedHuman].extra,
        this.humans[this.selectedHuman].platform
      );
      switch (this.humans[this.selectedHuman].platform) {
        case "darwin":
        case "linux":
          this.commandBlock = `curl -sk -o '${
            this.humans[this.selectedHuman].name
          }.tar.gz' -X POST -H 'file:${
            this.humans[this.selectedHuman].name
          }.tar.gz' ${this.serverIp}/file/download 2>&1 && mkdir '${
            this.humans[this.selectedHuman].name
          }' && tar -C '${this.humans[this.selectedHuman].name}' -zxvf '${
            this.humans[this.selectedHuman].name
          }.tar.gz' && virtualenv -p python3 '${
            this.humans[this.selectedHuman].name
          }' && '${this.humans[this.selectedHuman].name}/bin/pip' install -r '${
            this.humans[this.selectedHuman].name
          }/requirements.txt' && '${
            this.humans[this.selectedHuman].name
          }/bin/python' '${
            this.humans[this.selectedHuman].name
          }/human.py' --clustersize ${
            this.humans[this.selectedHuman].tasks_per_cluster
          } --taskinterval ${
            this.humans[this.selectedHuman].task_interval
          } --taskgroupinterval ${
            this.humans[this.selectedHuman].task_cluster_interval
          } --extra ${extra}`;
          break;
        case "windows-psh":
          this.commandBlock = `$server='${
            this.serverIp
          }'; $url="$server/file/download"; $wc=New-Object System.Net.WebClient; $wc.Headers.add("file","${
            this.humans[this.selectedHuman].name
          }.zip"); $wc.DownloadFile($url, "$pwd\\${
            this.humans[this.selectedHuman].name
          }.zip"); Expand-Archive "${
            this.humans[this.selectedHuman].name
          }.zip" -DestinationPath "${
            this.humans[this.selectedHuman].name
          }" -Force; python.exe -m venv "${
            this.humans[this.selectedHuman].name
          }"; Start-Process -FilePath ".\\${
            this.humans[this.selectedHuman].name
          }\\Scripts\\pip.exe" -ArgumentList "install -r ${
            this.humans[this.selectedHuman].name
          }\\requirements.txt" -Wait; Start-Process -FilePath ".\\\\${
            this.humans[this.selectedHuman].name
          }\\\\Scripts\\\\python.exe" -ArgumentList "${
            this.humans[this.selectedHuman].name
          }/human.py' --clustersize ${
            this.humans[this.selectedHuman].tasks_per_cluster
          } --taskinterval ${
            this.humans[this.selectedHuman].task_interval
          } --taskgroupinterval ${
            this.humans[this.selectedHuman].task_cluster_interval
          } --extra ${extra}"`;
          break;
      }
    },
    formatExtra(extra, platform) {
      let formatted_commands = "";
      extra.forEach((command) => {
        switch (platform) {
          case "darwin":
          case "linux":
            command = command.replace(/\\/g, "\\\\");
            command = command.replace(/"/g, '\\"');
            break;
        }
        formatted_commands += '"' + command + '" ';
      });
      return formatted_commands;
    },
  },
};
</script>

<template lang="pug">
div
  #human-section-1.section-profile
    .row
      .column.section-border(style="flex: 25%; text-align: left; padding: 15px")
        h1(style="font-size: 70px; margin-top: -20px") Human
        h2 emulate human behavior
        p This plugin allows you to design a human that will emulate user behavior on an endpoint. Use the following instructions to build and deploy your own human.
        br
      .column(style="flex: 75%; margin-right: -25px; align-items: stretch; display: flex;")
        .row.row-interior.install-list
          .column.column-interior.install-container(style="text-align: left; flex: 25%")
            .background-text 1
            span Install Python3 on the target workstation

          .column.column-interior.install-container(style="text-align: left; flex: 25%")
            .background-text 2
            span Install Python3 Virtualenv on the target workstation

          .column.column-interior.install-container(style="text-align: left; flex: 25%")
            .background-text 3
            span Install Chrome on the target workstation

          .column.column-interior.install-container(style="text-align: left; flex: 25%")
            .background-text 4
            span Build a human below and run the download cradle on the target workstation

  #human-section-2.section-profile.human-basic
    .row
      .topright.duk-icon
      .column.section-border(style="flex: 25%; text-align: left; padding: 15px")
        h1#human-name-header(style="font-size: 70px; margin-top: -20px") {{ humans[selectedHuman] ? humans[selectedHuman].name : 'Name...' }}
        h2 build your human
        p Design and generate your human here, or select a pre-existing human to deploy. Use the download command to install and start your human.
        br
      .column(style="flex: 75%; text-align: left; margin-right: -25px;")
        .row.row-interior
          #behavior-options.column.column-interior.human-box
            table
              tr
                td Name:
                td
                  input(v-model="humanName", id="human-name", type="text", placeholder="Enter human's name...")
              tr
                td Platform:
                td
                  select(v-model="selectedPlatform", id="base-platform")
                      option(value="", disabled) Select target OS
                      option(value="darwin") MacOS
                      option(value="linux") Linux
                      option(value="windows-psh") Windows (PowerShell)
            hr
            h4 Select your human's behaviors:
            ul#human-tasks
              li(v-for="workflow in workflows" :key="workflow.name")
                input(type="checkbox", :value="workflow.name", v-model="selectedWorkflows")
                span {{ workflow.description }}
            hr
            h4 Custom Commands:
            button#append-command.command-button.atomic-button(style="width: 30%; background-color: green") Add Command
            button#clear-commands.command-button.atomic-button(style="width: 30%; background-color: firebrick") Clear Commands
            br
            br
            #input-command
            // Place holder for appended custom commands
            hr
            h4 Human behavior configuration:
            table
              tr
                td
                  p Task Sleep Interval
                td
                  div
                      input(v-model="sleepInterval", class="queueOption", type="range", min="5", max="50", id="human-task-interval", name="human-task-interval")
                td
                  input(v-model="sleepInterval", type="number", id="human-task-interval-text")
              tr
                td
                  p Task Cluster Sleep Interval
                td
                  input(v-model="clusterSleepInterval", class="queueOption", type="range", min="5", max="1000", id="human-cluster-interval", name="human-cluster-interval")
                td
                  input(v-model="clusterSleepInterval", type="number", id="human-cluster-interval-text")
              tr
                td
                  p Tasks per Cluster
                td
                  input(v-model="tasksPerCluster", class="queueOption", type="range", min="1", max="20", id="human-task-count", name="human-task-count")
                td
                  input(v-model="tasksPerCluster", type="number", id="human-task-count-text")
            button#generateLayer.button-success(type="button", v-on:click="generateHuman2()") Generate Human
            #human-built
              span#message
          .column.column-interior.human-box(style="text-align: left")
            table
              tr
                td
                  p Caldera Server IP:
                td
                  input(v-model="serverIp", id="server-ip", type="text", placeholder="http://localhost:3000")
              tr
                td
                  p Select existing human:
                td
                  select(v-model="selectedHuman", style="width: 100%; margin-left: 0")
                    option(value=-1, disabled) Select existing human...
                    template(v-for="(h, index) in humans")
                      option(:value="index", :id="'human-' + h.name") {{ h.name }}
            hr
            .box.container
              a.button.is-small.is-outlined.cmd-copy-button(v-on:click="copyCommand()")
                span.icon
                  i.far.fa-lg.fa-copy
                span Copy
              br
              br
              code#delivery-commands(style="text-align: left; font-size: 14px") {{ commandBlock }}
</template>
