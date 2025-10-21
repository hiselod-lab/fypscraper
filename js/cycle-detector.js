/**
 * Cycle Detector Module
 * Implements DFS algorithm to detect circular references in the graph
 */

/**
 * Build adjacency list from graph data
 * @param {Object} graphData - Graph data with nodes and edges
 * @returns {Map} - Adjacency list (nodeId -> [targetIds])
 */
function buildAdjacencyList(graphData) {
    const adjList = new Map();

    // Initialize adjacency list for all nodes
    for (const node of graphData.nodes) {
        adjList.set(node.data.id, []);
    }

    // Add edges (only circular references for cycle detection)
    for (const edge of graphData.edges) {
        if (edge.data.refType === 'circular') {
            const sourceId = edge.data.source;
            const targetId = edge.data.target;

            if (adjList.has(sourceId)) {
                adjList.get(sourceId).push({
                    target: targetId,
                    edgeId: edge.data.id
                });
            }
        }
    }

    return adjList;
}

/**
 * Detect cycles using DFS with recursion stack
 * @param {Object} graphData - Graph data with nodes and edges
 * @returns {Object} - Cycle detection results
 */
function detectCycles(graphData) {
    console.log('Running cycle detection...');

    const adjList = buildAdjacencyList(graphData);
    const visited = new Set();
    const recursionStack = new Set();
    const cycles = [];
    const nodesInCycles = new Set();
    const edgesInCycles = new Set();

    /**
     * DFS function for cycle detection
     * @param {string} nodeId - Current node ID
     * @param {Array} path - Current path
     * @param {Array} edgePath - Current edge path
     */
    function dfs(nodeId, path, edgePath) {
        visited.add(nodeId);
        recursionStack.add(nodeId);
        path.push(nodeId);

        const neighbors = adjList.get(nodeId) || [];

        for (const neighbor of neighbors) {
            const targetId = neighbor.target;
            const edgeId = neighbor.edgeId;

            if (recursionStack.has(targetId)) {
                // Cycle detected!
                const cycleStartIndex = path.indexOf(targetId);

                if (cycleStartIndex !== -1) {
                    const cycle = path.slice(cycleStartIndex);
                    const cycleEdges = edgePath.slice(cycleStartIndex);
                    cycleEdges.push(edgeId); // Add the edge that closes the cycle

                    cycles.push({
                        nodes: cycle,
                        edges: cycleEdges,
                        length: cycle.length
                    });

                    // Mark all nodes in this cycle
                    for (const cycleNodeId of cycle) {
                        nodesInCycles.add(cycleNodeId);
                    }

                    // Mark all edges in this cycle
                    for (const cycleEdgeId of cycleEdges) {
                        edgesInCycles.add(cycleEdgeId);
                    }

                    console.log(`Found cycle: ${cycle.join(' → ')} → ${targetId}`);
                }

            } else if (!visited.has(targetId)) {
                // Continue DFS
                dfs(targetId, [...path], [...edgePath, edgeId]);
            }
        }

        recursionStack.delete(nodeId);
    }

    // Run DFS from all unvisited nodes (handles disconnected components)
    for (const node of graphData.nodes) {
        const nodeId = node.data.id;
        if (!visited.has(nodeId)) {
            dfs(nodeId, [], []);
        }
    }

    console.log(`Detected ${cycles.length} cycle(s) involving ${nodesInCycles.size} node(s)`);

    return {
        cycles: cycles,
        cycleCount: cycles.length,
        nodesInCycles: nodesInCycles,
        edgesInCycles: edgesInCycles,
        stats: {
            totalCycles: cycles.length,
            totalNodesInCycles: nodesInCycles.size,
            totalEdgesInCycles: edgesInCycles.size
        }
    };
}

/**
 * Apply cycle information to graph data
 * @param {Object} graphData - Graph data
 * @param {Object} cycleInfo - Cycle detection results
 */
function applyCycleInfo(graphData, cycleInfo) {
    console.log('Applying cycle information to graph...');

    // Mark nodes that are in cycles
    for (const node of graphData.nodes) {
        if (cycleInfo.nodesInCycles.has(node.data.id)) {
            node.data.inCycle = true;

            // Find which cycles this node belongs to
            node.data.cycleIds = [];
            for (let i = 0; i < cycleInfo.cycles.length; i++) {
                if (cycleInfo.cycles[i].nodes.includes(node.data.id)) {
                    node.data.cycleIds.push(i);
                }
            }
        }
    }

    // Mark edges that are part of cycles
    for (const edge of graphData.edges) {
        if (cycleInfo.edgesInCycles.has(edge.data.id)) {
            edge.data.isCycleEdge = true;

            // Find which cycles this edge belongs to
            edge.data.cycleIds = [];
            for (let i = 0; i < cycleInfo.cycles.length; i++) {
                if (cycleInfo.cycles[i].edges.includes(edge.data.id)) {
                    edge.data.cycleIds.push(i);
                }
            }
        }
    }

    console.log(`Marked ${cycleInfo.nodesInCycles.size} nodes and ${cycleInfo.edgesInCycles.size} edges as part of cycles`);
}

/**
 * Get cycle details for a specific node
 * @param {string} nodeId - Node ID
 * @param {Object} cycleInfo - Cycle detection results
 * @returns {Array} - Array of cycles this node belongs to
 */
function getCyclesForNode(nodeId, cycleInfo) {
    const nodeCycles = [];

    for (let i = 0; i < cycleInfo.cycles.length; i++) {
        if (cycleInfo.cycles[i].nodes.includes(nodeId)) {
            nodeCycles.push({
                id: i,
                nodes: cycleInfo.cycles[i].nodes,
                length: cycleInfo.cycles[i].length
            });
        }
    }

    return nodeCycles;
}

/**
 * Format cycle for display
 * @param {Object} cycle - Cycle object
 * @returns {string} - Formatted cycle string
 */
function formatCycle(cycle) {
    return cycle.nodes.join(' → ') + ' → ' + cycle.nodes[0];
}
