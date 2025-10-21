/**
 * Graph Builder Module
 * Extracts nodes and edges from loaded data and builds graph model
 */

// Global storage for nodes and edges
let allNodes = new Map();
let allEdges = [];
let nodeIdToNormalizedId = new Map();

/**
 * Department color mapping
 */
const DEPARTMENT_COLORS = {
    'ACD': '#66cc99',       // Green
    'AC&MFD': '#ffcc66',    // Yellow
    'ACMFD': '#ffcc66',     // Yellow (same as AC&MFD)
    'BPRD': '#6699ff',      // Blue
    'BSD': '#cc99ff',       // Purple
    'BSRVD': '#ff99cc',     // Pink
    'BPD': '#99ccff',       // Light Blue
    'Other': '#cccccc'      // Gray
};

/**
 * Get department color
 * @param {string} department - Department code
 * @returns {string} - Color hex code
 */
function getDepartmentColor(department) {
    return DEPARTMENT_COLORS[department] || DEPARTMENT_COLORS['Other'];
}

/**
 * Extract circulars from main file
 * @param {Object} fileData - Parsed JSON data
 * @param {Array} nodes - Nodes array to populate
 * @param {Array} edges - Edges array to populate
 */
function extractCircularsFromMainFile(fileData, nodes, edges) {
    if (!fileData || !fileData.years) return;

    const department = fileData.department || 'Other';

    // Iterate through years
    for (const [year, yearData] of Object.entries(fileData.years)) {
        // Process circulars array
        const circulars = yearData.circulars || [];
        for (const circular of circulars) {
            processCircular(circular, department, nodes, edges);
        }

        // Process circular_letters array
        const circularLetters = yearData.circular_letters || [];
        for (const letter of circularLetters) {
            processCircular(letter, department, nodes, edges);
        }
    }
}

/**
 * Process a single circular (extract node and references)
 * @param {Object} circular - Circular object
 * @param {string} department - Department code
 * @param {Array} nodes - Nodes array
 * @param {Array} edges - Edges array
 */
function processCircular(circular, department, nodes, edges) {
    if (!circular) return;

    const nodeId = circular.ID || generateNodeId(null, circular.url, circular.title);
    const year = extractYearFromDate(circular.date);

    // Create circular node
    const node = {
        id: nodeId,
        label: nodeId,
        title: circular.title || nodeId,
        date: circular.date || '',
        year: year,
        department: department,
        url: circular.url || '',
        content: circular.content || [],
        type: 'circular',
        refCount: 0,
        fromCache: false
    };

    nodes.push(node);

    // Map normalized ID for reference matching
    const normalizedId = normalizeTitle(nodeId);
    nodeIdToNormalizedId.set(normalizedId, nodeId);

    // Process references
    if (circular.references && Array.isArray(circular.references)) {
        extractReferences(circular.references, nodeId, department, nodes, edges);
    }
}

/**
 * Extract references recursively
 * @param {Array} references - References array
 * @param {string} sourceId - Source node ID
 * @param {string} department - Department code
 * @param {Array} nodes - Nodes array
 * @param {Array} edges - Edges array
 * @param {number} depth - Current recursion depth
 */
function extractReferences(references, sourceId, department, nodes, edges, depth = 0) {
    if (!references || !Array.isArray(references) || depth > 10) return;

    for (const ref of references) {
        if (!ref) continue;

        if (ref.type === 'circular') {
            // Create edge for circular reference
            const targetId = normalizeTitle(ref.title || '');
            if (targetId) {
                edges.push({
                    source: sourceId,
                    target: targetId,
                    refType: 'circular',
                    refTitle: ref.title || '',
                    refUrl: ref.url || ''
                });
            }

            // Process nested references
            if (ref.content && ref.content.references) {
                extractReferences(ref.content.references, sourceId, department, nodes, edges, depth + 1);
            }

        } else if (ref.type === 'pdf') {
            // Create PDF node
            const pdfId = ref.url || `pdf_${ref.title || Math.random()}`;

            const pdfNode = {
                id: pdfId,
                label: ref.title || 'PDF Document',
                title: ref.title || 'PDF Document',
                url: ref.url || '',
                type: 'pdf',
                department: department,
                refCount: 0,
                fromCache: false
            };

            nodes.push(pdfNode);

            // Create edge to PDF
            edges.push({
                source: sourceId,
                target: pdfId,
                refType: 'pdf',
                refTitle: ref.title || 'PDF Document',
                refUrl: ref.url || ''
            });

            // Process nested references in PDF content
            if (ref.content && ref.content.references) {
                extractReferences(ref.content.references, pdfId, department, nodes, edges, depth + 1);
            }

        } else if (ref.type === 'web') {
            // Create web reference node
            const webId = ref.url || `web_${ref.title || Math.random()}`;

            const webNode = {
                id: webId,
                label: ref.title || 'Web Link',
                title: ref.title || 'Web Link',
                url: ref.url || '',
                type: 'web',
                department: department,
                refCount: 0,
                fromCache: false
            };

            nodes.push(webNode);

            // Create edge to web reference
            edges.push({
                source: sourceId,
                target: webId,
                refType: 'web',
                refTitle: ref.title || 'Web Link',
                refUrl: ref.url || ''
            });
        }
    }
}

/**
 * Extract circulars from cache file
 * @param {Object} cacheData - Cache data object
 * @param {Array} nodes - Nodes array
 * @param {Array} edges - Edges array
 */
function extractCircularsFromCache(cacheData, nodes, edges) {
    if (!cacheData) return;

    for (const [circularId, circularData] of Object.entries(cacheData)) {
        const department = extractDepartmentFromId(circularId);

        // Create node
        const node = {
            id: circularId,
            label: circularId,
            title: circularId,
            department: department,
            type: 'circular',
            content: circularData.content ? circularData.content.content || [] : [],
            url: '',
            date: '',
            year: null,
            refCount: 0,
            fromCache: true
        };

        nodes.push(node);

        // Map normalized ID
        const normalizedId = normalizeTitle(circularId);
        nodeIdToNormalizedId.set(normalizedId, circularId);

        // Extract references from cached content
        if (circularData.content && circularData.content.references) {
            extractReferences(circularData.content.references, circularId, department, nodes, edges);
        }
    }
}

/**
 * Deduplicate nodes by ID
 * @param {Array} nodes - Nodes array
 * @returns {Map} - Deduplicated nodes map
 */
function deduplicateNodes(nodes) {
    const nodeMap = new Map();

    for (const node of nodes) {
        const existingNode = nodeMap.get(node.id);

        if (existingNode) {
            // Merge node data (prefer non-cache data)
            if (!node.fromCache || existingNode.fromCache) {
                // Update with more complete data
                if (node.title && !existingNode.title) existingNode.title = node.title;
                if (node.date && !existingNode.date) existingNode.date = node.date;
                if (node.year && !existingNode.year) existingNode.year = node.year;
                if (node.url && !existingNode.url) existingNode.url = node.url;
                if (node.content && node.content.length > 0 && existingNode.content.length === 0) {
                    existingNode.content = node.content;
                }
                if (!existingNode.fromCache) existingNode.fromCache = node.fromCache;
            }
        } else {
            nodeMap.set(node.id, node);
        }
    }

    return nodeMap;
}

/**
 * Validate and resolve edges
 * @param {Array} edges - Edges array
 * @param {Map} nodeMap - Nodes map
 * @returns {Array} - Valid edges array
 */
function validateEdges(edges, nodeMap) {
    const validEdges = [];
    let orphanedCount = 0;

    for (const edge of edges) {
        // Resolve target using normalized ID mapping
        let targetId = edge.target;

        // Try to find actual node ID using normalized mapping
        if (!nodeMap.has(targetId) && nodeIdToNormalizedId.has(targetId)) {
            targetId = nodeIdToNormalizedId.get(targetId);
        }

        // Check if both source and target exist
        if (nodeMap.has(edge.source) && nodeMap.has(targetId)) {
            validEdges.push({
                ...edge,
                target: targetId,
                id: `edge_${edge.source}_${targetId}_${validEdges.length}`
            });
        } else {
            orphanedCount++;
        }
    }

    if (orphanedCount > 0) {
        console.warn(`${orphanedCount} orphaned references (target not found)`);
    }

    return validEdges;
}

/**
 * Calculate reference counts for nodes
 * @param {Map} nodeMap - Nodes map
 * @param {Array} edges - Edges array
 */
function calculateReferenceCounts(nodeMap, edges) {
    // Count incoming references for each node
    for (const edge of edges) {
        const targetNode = nodeMap.get(edge.target);
        if (targetNode) {
            targetNode.refCount = (targetNode.refCount || 0) + 1;
        }
    }
}

/**
 * Build graph from loaded data
 * @param {Object} loadedData - Loaded data from data-loader
 * @returns {Object} - Graph data with nodes and edges
 */
function buildGraph(loadedData) {
    console.log('Building graph model...');

    const nodes = [];
    const edges = [];

    // Reset global mappings
    nodeIdToNormalizedId.clear();

    // Extract from main files
    for (const fileData of loadedData.mainFiles) {
        extractCircularsFromMainFile(fileData, nodes, edges);
    }

    // Extract from cache
    if (loadedData.cache) {
        extractCircularsFromCache(loadedData.cache, nodes, edges);
    }

    console.log(`Extracted: ${nodes.length} nodes (before deduplication), ${edges.length} edges`);

    // Deduplicate nodes
    const nodeMap = deduplicateNodes(nodes);
    console.log(`Deduplicated: ${nodeMap.size} unique nodes`);

    // Validate edges
    const validEdges = validateEdges(edges, nodeMap);
    console.log(`Validated: ${validEdges.length} valid edges`);

    // Calculate reference counts
    calculateReferenceCounts(nodeMap, validEdges);

    // Store globally
    allNodes = nodeMap;
    allEdges = validEdges;

    // Build Cytoscape-compatible data structure
    const cyNodes = [];
    const cyEdges = [];

    // Convert nodes
    for (const [id, node] of nodeMap) {
        cyNodes.push({
            data: {
                id: node.id,
                label: node.label,
                title: node.title,
                date: node.date,
                year: node.year,
                department: node.department,
                departmentColor: getDepartmentColor(node.department),
                url: node.url,
                content: node.content,
                type: node.type,
                refCount: node.refCount,
                fromCache: node.fromCache,
                inCycle: false,
                cycleIds: []
            }
        });
    }

    // Convert edges
    for (const edge of validEdges) {
        cyEdges.push({
            data: {
                id: edge.id,
                source: edge.source,
                target: edge.target,
                refType: edge.refType,
                refTitle: edge.refTitle,
                refUrl: edge.refUrl,
                isCycleEdge: false,
                cycleIds: []
            }
        });
    }

    console.log(`Built Cytoscape data: ${cyNodes.length} nodes, ${cyEdges.length} edges`);

    return {
        nodes: cyNodes,
        edges: cyEdges,
        nodeMap: nodeMap,
        stats: {
            totalNodes: cyNodes.length,
            totalEdges: cyEdges.length,
            circularNodes: cyNodes.filter(n => n.data.type === 'circular').length,
            pdfNodes: cyNodes.filter(n => n.data.type === 'pdf').length,
            webNodes: cyNodes.filter(n => n.data.type === 'web').length
        }
    };
}
