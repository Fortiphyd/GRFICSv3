import * as Terminal from "./xterm.js";
import * as FitAddon from "./xterm-addon-fit.min.js";

// run terminal emulator
let input = "";
let shellHistory = [];
let shellHistoryIndex = 0;

// build terminal emulator
let prompt = "~$ ";
let term;
let fitAddon;

export async function loadCommand(api) {
  if (!initTerm()) return;
  const el = document.getElementById("session-id");
  el.addEventListener("change", () => {
    clearTerminal();
    getShellHistory(el, api);
  });


  term?.onData((data) => {
    const code = data.charCodeAt(0);
    if (code === 13) {
      if (input !== "" && !checkSpecialKeywords(input)) {
        runCommand(input);
        shellHistory.pop();
        shellHistory.push(input);
        shellHistory.push("");
        shellHistoryIndex = shellHistory.length - 1;
      } else {
        term.write(`\r\n${prompt}`);
      }
      input = "";
    } else if (code === 127) {
      if (input.length > 0) {
        term.write("\b \b");
        input = input.substr(0, input.length - 1);
      }
    } else if (code === 27) {
      updateHistory(data);
    } else if (code < 32) {
      return;
    } else {
      term.write(data);
      input += data;
    }
  });
}

export function setCommand(cmd) {
  term.write(cmd);
  input = cmd;
}

function initTerm() {
  if (!document.querySelector("#manxPage")) {
    term = null;
    return false;
  }
  term = new window.Terminal();
  fitAddon = new window.FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.setOption("cursorBlink", true);
  term.open(document.getElementById("xterminal"));
  fitAddon.fit();
  term.write(prompt);
  return true;
}

function updateHistory(data) {
  if (shellHistory.length > 0) {
    if (data.localeCompare("[A") === 0) {
      handleUpArrow();
    } else if (data.localeCompare("[B") === 0) {
      handleDownArrow();
    }
  }
}

function handleUpArrow() {
  if (shellHistoryIndex > 0) {
    shellHistoryIndex--;
    writeHistory(shellHistory[shellHistoryIndex]);
  }
}

function handleDownArrow() {
  if (shellHistoryIndex < shellHistory.length - 1) {
    shellHistoryIndex++;
    writeHistory(shellHistory[shellHistoryIndex]);
  }
}

function writeHistory(value) {
  term.write(`\x1b[2K\r${prompt}`);
  term.write(value);
  input = value;
}

function getShellHistory(elem, api) {
  if (elem.options && elem.selectedIndex)
    api.post("/plugin/manx/history",
      { paw: elem.options[elem.selectedIndex].getAttribute("data-paw") },
    ).then((data) => populateHistory(data));
}

function populateHistory(data) {
  if (data.length > 0) {
    for (let index in data) {
      shellHistory.push(data[index]["cmd"]);
    }
    shellHistory.push("");
    shellHistoryIndex = shellHistory.length - 1;
  }
}

function displayHistory() {
  for (let i = 0; i < shellHistory.length - 1; i++) {
    term.write(`\r\n[${i}]  ${shellHistory[i]}`);
  }
}

function checkSpecialKeywords(word) {
  if (word.localeCompare("history") === 0) {
    console.log("displaying history");
    displayHistory();
    return true;
  }
  return false;
}

function runCommand(cmd) {
  const el = document.getElementById("session-id");
  let sessionId = el.options[el.selectedIndex].value;
  let [wsHost, wsPort] = document
    .getElementById("websocket-data")
    .getAttribute("data-websocket")
    .split(":");

  if (wsHost === "0.0.0.0") {
    console.log(
      "WebSocket host configured for 0.0.0.0. Using window location for host/ip instead."
    );
    wsHost = window.location.hostname;
  }

  const wsProto = location.protocol == "https:" ? "wss://" : "ws://";

  const x = `${wsProto + wsHost}:${wsPort}/manx/${sessionId}`;
  const socket = new WebSocket(x);

  socket.onopen = function () {
    socket.send(cmd);
  };

  socket.onmessage = function (s) {
    try {
      let jData = JSON.parse(s.data);
      let lines = jData.response.split("\n");
      for (let i = 0; i < lines.length; i++) {
        term.write(`\r\n${lines[i]}`);
      }
      prompt = `${jData.pwd}$ `;
      term.write(`\r\n${prompt}`);
    } catch (err) {
      term.write("\r\nDead session. Probably. It has been removed.");
      clearTerminal();
      el.selectedIndex = 0;
    }
  };
}

function clearTerminal() {
  term.write(`\x1b[2K\r`);
  term.clear();
  shellHistory = [];
  shellHistoryIndex = 0;
  input = "";
  prompt = "~$ ";
  term.write(`\r${prompt}`);
}

//# sourceURL=manxterm.js
