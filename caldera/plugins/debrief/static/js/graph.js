// Constants are wrapped in a function to prevent redeclarations when tab is closed and openned again
function global() {
    return {
        FACT_DISPLAY_LIMIT: 15,

        OP_GRAPH_HEIGHT: 400,
        FACT_GRAPH_WIDTH: 800,
        FACT_GRAPH_HEIGHT: 600,

        LINK_LENGTHS: {
            agent_contact: 100, 
            next_link: 50, 
            has_agent: 50, 
            relationship: 100
        },
        NODE_CHARGES: {
            c2: -200, 
            operation: -100, 
            agent: -200, 
            link: -150, 
            fact: -50, 
            tactic: -200, 
            technique_name: -200
        },
        GRAPH_IMAGE_URLS: {
            server: '/debrief/img/cloud.svg',
            operation: '/debrief/img/operation.svg',
            link: '/debrief/img/link.svg',
            fact: '/debrief/img/star.svg',
            darwin: '/debrief/img/darwin.svg',
            windows: '/debrief/img/windows.svg',
            linux: '/debrief/img/linux.svg',
            tactic: '/debrief/img/tactic.svg',
            technique_name: '/debrief/img/technique.svg',
            collection: '/debrief/img/collection.svg',
            'credential-access': '/debrief/img/credaccess.svg',
            'defense-evasion': '/debrief/img/defevasion.svg',
            discovery: '/debrief/img/discovery.svg',
            execution: '/debrief/img/execution.svg',
            exfiltration: '/debrief/img/exfil.svg',
            impact: '/debrief/img/impact.svg',
            'lateral-movement': '/debrief/img/latmove.svg',
            persistence: '/debrief/img/persistence.svg',
            'privilege-escalation': '/debrief/img/privesc.svg',
            'initial-access': '/debrief/img/access.svg',
            'command-and-control': '/debrief/img/commandcontrol.svg',
            unknown: '/debrief/img/unknown.svg'
        }
    }
}

function init() {
    getImages();
}

function apiV2(requestType, endpoint, body = null, jsonRequest = true) {
    let requestBody = { method: requestType };
    if (jsonRequest) {
        requestBody.headers = { 'Content-Type': 'application/json' };
        if (body) {
            requestBody.body = JSON.stringify(body);
        }
    } else {
        if (body) {
            requestBody.body = body;
        }
    }

    return new Promise((resolve, reject) => {
        fetch(endpoint, requestBody)
            .then((response) => {
                if (!response.ok) {
                    reject(response.statusText);
                }
                return response.text();
            })
            .then((text) => {
                try {
                    resolve(JSON.parse(text));
                } catch {
                    resolve(text);
                }
            });
    });
}
function getImages() {
    for (let key in global().GRAPH_IMAGE_URLS) {
        fetch(global().GRAPH_IMAGE_URLS[key]).then((data) => {
            return data.text();
        }).then((svg) => {
            let parser = new DOMParser();
	        let doc = parser.parseFromString(svg, 'text/html');
            let child = doc.body.firstChild;
            child.id = key + '-img';
            child.classList.add('svg-icon');
            document.getElementById('images').append(child);
        });
    }
}

function statusName(status) {
    if (status === 0) {
        return 'success';
    } else if (status === -2) {
        return 'discarded';
    } else if (status === 1) {
        return 'failure';
    } else if (status === 124) {
        return 'timeout';
    } else if (status === -3) { // && chain.collect) {
        return 'collected';
    } else if (status === -4) {
        return 'untrusted';
    } else if (status === -5) {
        return 'visibility';
    }
    return 'queued';
}

function createForceSimulation(type) {
    let opGraphWidth = document.getElementById('debrief-graph').offsetWidth;
    let width = (type === 'operation') ? opGraphWidth : global().FACT_GRAPH_WIDTH;
    let height = (type === 'operation') ? global().OP_GRAPH_HEIGHT : global().FACT_GRAPH_HEIGHT;
    return d3.forceSimulation()
            .force('link', d3.forceLink().id((d) => d.id ))
            .force('charge', d3.forceManyBody()
                .strength((d) => global().NODE_CHARGES[d.type] || -200)
                .theta(0.8)
                .distanceMax(100))
            .force('center', d3.forceCenter((width - 200) / 2, height / 2))
            .force('collision', d3.forceCollide().radius(40));
}

function updateReportGraph(operations) {
    Array.from(document.getElementsByClassName('debrief-svg')).forEach((svg) => svg.innerHTML = '');
    d3.selectAll('.debrief-svg > *').remove();

    graphs = [
        { id: '#debrief-steps-svg', type: 'steps', tooltip: d3.select('#op-tooltip'), simulation: createForceSimulation('operation'), svg: d3.select('#debrief-steps-svg') },
        { id: '#debrief-attackpath-svg', type: 'attackpath', tooltip: d3.select('#op-tooltip'), simulation: createForceSimulation('operation'), svg: d3.select('#debrief-attackpath-svg') },
        { id: '#debrief-tactic-svg', type: 'tactic', tooltip: d3.select('#op-tooltip'), simulation: createForceSimulation('operation'), svg: d3.select('#debrief-tactic-svg') },
        { id: '#debrief-technique-svg', type: 'technique', tooltip: d3.select('#op-tooltip'), simulation: createForceSimulation('operation'), svg: d3.select('#debrief-technique-svg') },
        { id: '#debrief-fact-svg', type: 'fact', tooltip: d3.select('#fact-tooltip'), simulation: createForceSimulation('fact'), svg: d3.select('#debrief-fact-svg') }
    ]

    graphs.forEach((graph) => {
        apiV2('GET', `/plugin/debrief/graph?type=${graph.type}&operations=${operations.join()}`).then((graphData) => {
            graph.nodes = graphData.nodes;
            graph.links = graphData.links;

            writeGraph(graph);
            if (graph.type === 'fact') {
                limitFactsDisplayed(operations);
            }

            graph.simulation.alpha(1).restart();
            graph.svg.call(d3.zoom().scaleExtent([0.5, 5]).on('zoom', () => {
                d3.select(graph.id + ' .graphContainer')
                    .attr('transform', 'translate(' + d3.event.transform.x + ',' + d3.event.transform.y + ')scale(' + d3.event.transform.k + ')');
            }));
        }).catch((error) => {
            console.error('Fetch', error);
        });
    });
}

function writeGraph(graph) {
    graph.svg.append('defs').append('marker')
        .attr('id', `arrowhead${graph.type}`)
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 30)
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('xoverflow', 'visible')
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
        .attr('fill', '#999')
        .style('stroke','none');

    let container = graph.svg.append('g')
                        .attr('class', 'container')
                        .attr('width', '100%')
                        .attr('height', '100%')

    let graphContainer = container.append('g')
                        .attr('class', 'graphContainer')
    let arrows = graphContainer.append('g')
                .style('stroke', '#aaa')
                .style('fill', '#aaa')
                .selectAll('polyline')
                .data(graph.links)
                .enter().append('polyline')
                .attr('data-source', (d) => d.source)
                .attr('data-target', (d) => d.target)
                .attr('class', (d) => d.type)
                .attr('stroke-linecap', 'round');

    container.selectAll('g.nodes').remove();
    let nodes = graphContainer.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(graph.nodes)
        .enter().append('g')
            .attr('data-op', (d) => d.operation)
            .attr('id', (d) => `node-${d.id}`)
            .attr('class', (d) => `node ${d.type}`)
            .attr('data-timestamp', (d) => d.timestamp)
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));

    nodes.append('circle')
        .attr('r', 16)
        .style('fill', (d) => (d.status || d.status == 0) ? statusColor(d.status) : '#efefef')
        .style('stroke', '#424242')
        .style('stroke-width', '1px')

    nodes.append('text')
        .attr('class', 'label')
        .attr('x', '18')
        .attr('y', '8')
        .style('font-size', '12px').style('fill', 'white')
        .text((d) => {
            if (d.type != 'link') {
                return d.name;
            }
        });

    nodes.append('g')
        .attr('class', 'icons')
        .html((d) => {
            let c = updateIconAttr(cloneImgIcon(d), d.status);
            let l = '';
            if (d.type == 'link') {
                l = document.getElementById('link-img').cloneNode(true);
                l = updateIconAttr(l, d.status);
                c.classList.add('hidden');
                c.style.display = 'none';
            }
            return c.outerHTML + l.outerHTML;
        })

    createLegend(container, graph);

    let simulation = graph.simulation;

    simulation
        .nodes(graph.nodes)
        .on('tick', ticked)
        .force('link')
        .links(graph.links)
        .distance((d) => global().LINK_LENGTHS[d.type]);

    function ticked() {
        arrows
            .attr('points', (d) => getPolylineCoords(d.source.x, d.source.y, d.target.x, d.target.y))
            .attr('transform', (d) => rotateArrow(d.source.x, d.source.y, d.target.x, d.target.y));

        nodes
            .attr('transform', (d) => 'translate(' + d.x + ',' + d.y + ')')
            .on('mouseover', (d, i) => {
                if (graph.tooltip) {
                    graph.tooltip.transition()
                        .duration(200)
                        .style('opacity', .9);
                    graph.tooltip.html(generateTooltipHTML(d))
                        .style('left', `${d.x + 10}px`)
                        .style('top', `${d.y + 10}px`);
                }
            })
            .on('mouseout', (d) => {
                if (graph.tooltip) {
                    graph.tooltip.transition()
                        .duration(500)
                        .style('opacity', 0);
                }
            });
    }

    function dragstarted(d) {
        if (!d3.event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
    }

    function dragged(d) {
        d.fx = d3.event.x
        d.fy = d3.event.y
    }

    function dragended(d) {
        d.fx = d3.event.x
        d.fy = d3.event.y
        if (!d3.event.active) simulation.alphaTarget(0);
    }

    function generateTooltipHTML(d) {
        let ret = '';
        switch (d['type']) {
            case 'operation':
                ret += 'name: ' + sanitize(d['name']) + '<br/>';
                ret += 'op_id: ' + d['id'] + '<br/>';
                ret += 'created: ' + d['timestamp'] + '<br/>';
                break;
            case 'tactic':
            case 'technique_name':
                let p = d['attrs'][d['type']]
                ret += d['type'] + ': ' + p + '<br/>';
                ret += 'created: ' + d['timestamp'] + '<br/>';
                for (let attr in d['attrs']) {
                    if (attr != d['type']) {
                        ret += sanitize(attr) + ': ' + sanitize(d['attrs'][attr]) + '<br/>';
                    }
                }
                break;
            default:
                ret += d['timestamp'] ? 'created: ' + d['timestamp'] + '<br/>' : '';
                for (let attr in d['attrs']) {
                    if (d['attrs'][attr] != null) {
                        ret += sanitize(attr) + ': ';
                        ret += attr == 'status' ? statusName(d['attrs'][attr]) : sanitize(d['attrs'][attr]);
                        ret += '<br/>';
                    }
                }
        }
        return ret;
    }

  function sanitize(unsafeMsg) {
    const parser = new DOMParser();
    let doc = parser.parseFromString(unsafeMsg, 'text/html');
    return doc.body.innerText;
  }
    function getPolylineCoords(x1, y1, x2, y2) {
        let p1 = `${x1} ${y1}`;
        let x = x1 - Math.hypot(x2-x1, y2-y1) + 17;
        let p2 = `${x} ${y1}`;
        let p3 = `${x + 7.5} ${y1 + 4}`;
        let p4 = `${x + 7.5} ${y1 - 4}`;
        let p5 = p2;
        return `${p1}, ${p2}, ${p3}, ${p4}, ${p5}`;
    }

    function rotateArrow(x1, y1, x2, y2) {
      let deltaX = x2 - x1;
      let deltaY = y2 - y1;
      let angleDeg = Math.atan2(deltaY, deltaX) * 180 / Math.PI + 180;
      return `rotate(${angleDeg}, ${x1}, ${y1})`;
    }
}

function createLegend(container, graph) {
    let opGraphWidth = document.getElementById('debrief-graph').offsetWidth;
    let width = (graph.type !== 'fact') ? opGraphWidth : global().FACT_GRAPH_WIDTH;
    let height = (graph.type !== 'fact') ? global().OP_GRAPH_HEIGHT : global().FACT_GRAPH_HEIGHT;
  
    let legend = container.append('g')
	    .attr('class', 'legend')

	legend.append('rect')
	    .attr('id', 'legend-rect-' + graph.type)
	    .attr('x', width - 193)
	    .attr('y', 10)
	    .attr('rx', 6)
	    .attr('width', 183)
	    .attr('height', 50)
	    .style('fill', 'rgba(170, 170, 170, 0.5)')

	legend.append('text')
	    .attr('x', width - 130)
	    .attr('y', 35)
	    .style('font-weight', 'bold')
	    .style('fill', 'white')
	    .text('Legend')

	let entry = legend.selectAll('g')
	    .data(graph.nodes.filter(isUniqueImg).concat(addLinkImg(graph.type)))
	    .enter()
	    .append('g')

    let lineHeight = 30;
    let upperPadding = 60;

    entry.append('svg')
        .attr('x', width - 180)
        .attr('y', (d, i) => {
            document.getElementById(`legend-rect-${graph.type}`).setAttribute('height', parseInt(document.getElementById(`legend-rect-${graph.type}`).getAttribute('height')) + lineHeight);
            let yVal = i * lineHeight + upperPadding;
            if (yVal > height - 80) {
                document.getElementById('debrief-graph').setAttribute('height', height + lineHeight);
                height = document.getElementById('debrief-graph').getAttribute('height');
            }
            return yVal;
        })
        .attr('width', 20)
        .attr('height', 20)
        .html(function (d) {
            let clone = cloneImgIcon(d);
            this.id = clone.id + '-legend';
            this.setAttribute('viewBox', clone.getAttribute('viewBox'));
            this.setAttribute('preserveAspectRatio', 'xMidYMid meet');
            this.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
            this.setAttribute('version', '1.0');
            return clone.innerHTML;
        })

    entry.append('text')
        .attr('x', width - 135)
        .attr('y', (d, i) => i *  lineHeight + upperPadding + lineHeight / 2)
        .style('fill', 'white')
        .style('font-size', 13)
        .style('text-transform', 'capitalize')
        .text((d) => d.img.indexOf(' ') == -1 ? d.img : d.type);

    if (graph.type === 'fact') {
        let legendHeight = 50 + parseInt(document.getElementById(`legend-rect-${graph.type}`).getAttribute('height'));

        let factCountTable  = legend.append('g')
            .attr('class', 'fact-count')

        let factEntry = factCountTable.selectAll('g')
            .data(graph.nodes.filter(x => x.type == 'fact').filter(isUniqueFactTrait))
            .enter()
            .append('g')

        factEntry.append('text')
            .attr('x', width - 190)
            .attr('y', (d, i) => legendHeight + i * 20)
            .style('fill', 'white')
            .style('font-size', 13)
            .text((d) => graph.nodes.filter(x => x.name == d.name).length)

        factEntry.append('text')
            .attr('x', width - 160)
            .attr('y', (d, i) => legendHeight + i * 20)
            .style('fill', 'white')
            .style('font-size', 13)
            .style('font-weight', 'normal')
            .text((d) => d.name)
    }
}

function moveLegend() {
    if (!graphs) return
    d3.selectAll('.legend').remove();
    graphs.forEach((graph) => {
        createLegend(d3.select(`${graph.id} > .container`), graph);
    });
}

function cloneImgIcon(d) {
    let c;
    try {
        if (d.img.indexOf(' ') === -1 && document.getElementById(`${d.img}-img`)) {
            c = document.getElementById(`${CSS.escape(d.img)}-img`).cloneNode(true);
        } else {
            c = document.getElementById(`${CSS.escape(d.type)}-img`).cloneNode(true);
        }
    } catch {
        c = document.getElementById('#unknown-img').cloneNode(true);
    }
    return c;
}

function updateIconAttr(svg, status) {
    svg.setAttribute('id', null);
    svg.setAttribute('width', 32);
    svg.setAttribute('height', 16);
    svg.setAttribute('x', '-16');
    svg.setAttribute('y', '-8');
    if (status && status == -2) {
        svg.children[0].setAttribute('fill', 'white');
    }
    return svg;
}

function statusColor(status) {
    if (status === 0) {
        return '#44AA99';
    } else if (status === -2) {
        return 'black';
    } else if (status === 1) {
        return '#CC3311';
    } else if (status === 124) {
        return 'cornflowerblue';
    } else if (status === -3) {
        return '#FFB000';
    } else if (status === -4) {
        return 'white';
    } else if (status === -5) {
        return '#EE3377';
    }
    return '#555555';
}

function limitFactsDisplayed(operations) {
    let hasOverFactLimit = operations.some((op) => Array.from(document.querySelectorAll(`#debrief-fact-svg g.fact[data-op="${op}"]`)).slice(global().FACT_DISPLAY_LIMIT).length > 0)
    if (hasOverFactLimit) {
        document.getElementById('fact-limit-msg').innerHTML = `More than ${global().FACT_DISPLAY_LIMIT} facts found in the operation(s) selected. For readability, only the first ${global().FACT_DISPLAY_LIMIT} facts of each operation are displayed.`;
        document.getElementById('fact-limit').style.display = '';
        operations.forEach((opId) => {
            let nodesToRemove = Array.from(document.querySelectorAll(`#debrief-fact-svg g.fact[data-op="${opId}"]`)).splice(global().FACT_DISPLAY_LIMIT);
            nodesToRemove.forEach((node) => {
                let nodeId = node.id.split('node-')[1];
                Array.from(document.querySelectorAll(`#debrief-fact-svg polyline.relationship[data-source="${nodeId}"]`)).forEach((el) => el.remove());
                Array.from(document.querySelectorAll(`#debrief-fact-svg polyline.relationship[data-target="${nodeId}"]`)).forEach((el) => el.remove());
                node.remove();
            })
        })
    } else {
        document.getElementById('fact-limit').style.display = 'none';
    }
}

function isUniqueImg(value, index, self) {
    let arr = Array.from(self, x => x.img.indexOf(' ') === -1 ? x.img : x.type);
    let v = value.img.indexOf(' ') === -1 ? value.img : value.type;
    return arr.indexOf(v) === index;
}

function addLinkImg(graphType) {
    return graphType == 'graph' ? [{'name': 'link-image', 'img': 'link'}] : [];
}

function isUniqueFactTrait(value, index, self) {
    let arr = Array.from(self, x => x.name);
    return arr.indexOf(value.name) === index;
}

init();
