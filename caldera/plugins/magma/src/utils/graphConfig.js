const config = {
  view: {
    // layoutHandler: new ForceLayout({
    //   positionFixedByDrag: false,
    //   positionFixedByClickWithAltKey: true,
    //   createSimulation: (d3, nodes, edges) => {
    //     // d3-force parameters
    //     const forceLink = d3.forceLink(edges).id((d) => d.id);
    //     return d3
    //       .forceSimulation(nodes)
    //       .force("edge", forceLink.distance(60).strength(0.2))
    //       .force("charge", d3.forceManyBody().strength(-200))
    //       .force("center", d3.forceCenter().strength(0.05))
    //       .alphaMin(0.001);
    //
    //     // * The following are the default parameters for the simulation.
    //     // const forceLink = d3.forceLink(edges).id((d) => d.id);
    //     // return d3
    //     //   .forceSimulation(nodes)
    //     //   .force("edge", forceLink.distance(100))
    //     //   .force("charge", d3.forceManyBody())
    //     //   .force("collide", d3.forceCollide(50).strength(0.2))
    //     //   .force("center", d3.forceCenter().strength(0.05))
    //     //   .alphaMin(0.001);
    //   },
    // }),
    scalingObjects: true,
    minZoomLevel: 0.5,
    maxZoomLevel: 1.5,
  },
  node: {
    selectable: 1,
    normal: {
      type: "circle",
      radius: 30,
      color: "#6C63FF",
    },
    hover: {
      color: "#8A85FF",
      strokeWidth: 3,
      strokeColor: "#D1CFE2",
      strokeDasharray: "0",
    },

    label: {
      visible: true,
      color: "white",
      fontFamily: "inherit",
      fontSize: 12,
      text: "name",
      margin: 8,
      background: {
        visible: true,
        color: "black",
        padding: {
          vertical: 2,
          horizontal: 4,
        },
        borderRadius: 5,
      },
    },
    focusring: {
      visible: true,
      width: 4,
      padding: 3,
      color: "#B3B1C4",
      dasharray: "15",
    },
  },
  edge: {
    gap: 12,
    normal: { color: "#6699cc" },
  },
  path: {
    visible: true,
    hoverable: true,
    margin: 20,
    normal: {
      linecap: "square",
      color: "#D1CFE2",
      width: 10,
      dasharray: "6 16",
      animate: true,
      animationSpeed: 40,
    },
    hover: {
      width: 12,
      color: "#ff000088",
      dasharray: "",
      linecap: "round",
      linejoin: "round",
      animate: false,
    },
  },
};
export default config;
