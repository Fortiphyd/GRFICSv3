export { getLinkStatus, LINK_STATUSES };

const LINK_STATUSES = {
  0: "success",
  "-1": "paused",
  1: "failed",
  "-2": "discarded",
  "-3": "collect",
  "-4": "untrusted",
  "-5": "visible",
  124: "timeout",
};

const LINK_COLORS = {
  0: "#4a9",
  "-1": "#ffc500",
  1: "#c31",
  "-2": "#a05195",
  "-3": "#ffb000",
  "-4": "white",
  "-5": "#f012be",
  124: "cornflowerblue",
};

function getLinkStatus(link) {
  return {
    color: LINK_COLORS[link.status.toString()],
    text: LINK_STATUSES[link.status.toString()],
  };
}
