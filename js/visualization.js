/**
 * Visualization Module
 * Handles Cytoscape initialization, layouts, and interactions
 */

// Global Cytoscape instance
let cy = null;
let currentLayout = 'forceDirected';

/**
 * Layout configurations
 */
const LAYOUTS = {
    forceDirected: {
        name: 'cose',
        animate: true,
        animationDuration: 500,
        nodeRepulsion: 8000,
        idealEdgeLength: 100,
        edgeElasticity: 100,
        nestingFactor: 1.2,
        gravity: 1,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0
    },
    hierarchical: {
        name: 'dagre',
        rankDir: 'TB',
        animate: true,
        animationDuration: 500,
        nodeSep: 50,
        rankSep: 100,
        padding: 30
    },
    radial: {
        name: 'concentric',
        animate: true,
        animationDuration: 500,
        concentric: function(node) {
            return node.data('refCount') || 0;
        },
        levelWidth: function() {
            return 2;
        },
        minNodeSpacing: 50,
        padding: 30
    }
};

/**
 * Initialize Cytoscape visualization
 * @param {Object} graphData - Graph data with nodes and edges
 */
function initializeVisualization(graphData) {
    console.log('Initializing Cytoscape...');

    // Create Cytoscape instance
    cy = cytoscape({
        container: document.getElementById('cy-container'),

        elements: {
            nodes: graphData.nodes,
            edges: graphData.edges
        },

        style: [
            // Circular nodes
            {
                selector: 'node[type="circular"]',
                style: {
                    'background-color': 'data(departmentColor)',
                    'width': function(ele) {
                        const refCount = ele.data('refCount') || 0;
                        return Math.max(40, Math.min(60, 40 + refCount * 2));
                    },
                    'height': function(ele) {
                        const refCount = ele.data('refCount') || 0;
                        return Math.max(40, Math.min(60, 40 + refCount * 2));
                    },
                    'border-width': 2,
                    'border-color': '#333',
                    'label': '',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '10px',
                    'color': '#333'
                }
            },

            // PDF nodes
            {
                selector: 'node[type="pdf"]',
                style: {
                    'background-color': '#ff9966',
                    'width': 25,
                    'height': 25,
                    'border-width': 2,
                    'border-color': '#333',
                    'shape': 'rectangle',
                    'label': '',
                    'font-size': '9px',
                    'color': '#333'
                }
            },

            // Web nodes
            {
                selector: 'node[type="web"]',
                style: {
                    'background-color': '#99ccff',
                    'width': 20,
                    'height': 20,
                    'border-width': 2,
                    'border-color': '#333',
                    'shape': 'diamond',
                    'label': '',
                    'font-size': '9px',
                    'color': '#333'
                }
            },

            // Nodes in cycles (orange glow)
            {
                selector: 'node[inCycle]',
                style: {
                    'border-width': 3,
                    'border-color': '#ff9933'
                }
            },

            // Edges
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#999',
                    'target-arrow-color': '#999',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1
                }
            },

            // Cycle edges (orange)
            {
                selector: 'edge[isCycleEdge]',
                style: {
                    'line-color': '#ff9933',
                    'target-arrow-color': '#ff9933',
                    'width': 3
                }
            },

            // Highlighted elements
            {
                selector: '.highlighted',
                style: {
                    'border-width': 4,
                    'border-color': '#ffcc00'
                }
            },

            // Dimmed elements
            {
                selector: '.dimmed',
                style: {
                    'opacity': 0.2
                }
            },

            // Hidden elements
            {
                selector: '.hidden',
                style: {
                    'display': 'none'
                }
            }
        ],

        layout: LAYOUTS.forceDirected,

        minZoom: 0.1,
        maxZoom: 5,
        wheelSensitivity: 0.2
    });

    console.log('Cytoscape initialized');

    // Set up event handlers
    setupEventHandlers();

    // Update statistics
    updateStatistics(graphData);

    // Load saved layout preference
    const savedLayout = localStorage.getItem('selectedLayout') || 'forceDirected';
    if (savedLayout !== 'forceDirected') {
        switchLayout(savedLayout);
    }
}

/**
 * Setup event handlers for interactions
 */
function setupEventHandlers() {
    // Node hover
    cy.on('mouseover', 'node', function(event) {
        const node = event.target;
        const position = event.position || event.cyPosition;

        // Show tooltip
        showTooltip(
            node.data('id'),
            node.data('title'),
            position.x,
            position.y
        );

        // Light highlight
        node.style('border-width', 3);
        node.connectedEdges().style('width', 3);
    });

    cy.on('mouseout', 'node', function(event) {
        hideTooltip();
        event.target.style('border-width', node => node.data('inCycle') ? 3 : 2);
        cy.edges().style('width', edge => edge.data('isCycleEdge') ? 3 : 2);
    });

    // Node click
    cy.on('tap', 'node', function(event) {
        const node = event.target;

        // Show details panel
        showDetailsPanel(node);

        // Highlight connections
        cy.elements().addClass('dimmed');
        node.removeClass('dimmed').addClass('highlighted');
        node.neighborhood().removeClass('dimmed');
        node.connectedEdges().removeClass('dimmed').style('width', 4);
    });

    // Node double-click (open URL)
    cy.on('dbltap', 'node', function(event) {
        const url = event.target.data('url');
        if (url && url.trim() !== '') {
            window.open(url, '_blank');
        }
    });

    // Edge hover
    cy.on('mouseover', 'edge', function(event) {
        const edge = event.target;
        const position = event.position || event.cyPosition;

        showEdgeTooltip(
            edge.data('refTitle'),
            edge.data('refType'),
            position.x,
            position.y
        );

        edge.style('width', 4);
    });

    cy.on('mouseout', 'edge', function(event) {
        hideTooltip();
        event.target.style('width', edge => edge.data('isCycleEdge') ? 3 : 2);
    });

    // Background click (deselect)
    cy.on('tap', function(event) {
        if (event.target === cy) {
            cy.elements().removeClass('dimmed highlighted');
            cy.edges().style('width', edge => edge.data('isCycleEdge') ? 3 : 2);
            hideDetailsPanel();
        }
    });
}

/**
 * Switch layout
 * @param {string} layoutName - Layout name (forceDirected, hierarchical, radial)
 */
function switchLayout(layoutName) {
    if (!LAYOUTS[layoutName]) {
        console.error(`Unknown layout: ${layoutName}`);
        return;
    }

    console.log(`Switching to ${layoutName} layout...`);

    currentLayout = layoutName;
    const layout = cy.layout(LAYOUTS[layoutName]);
    layout.run();

    // Save preference
    localStorage.setItem('selectedLayout', layoutName);

    // Update UI
    updateLayoutButtons(layoutName);
}

/**
 * Update layout button states
 * @param {string} activeLayout - Active layout name
 */
function updateLayoutButtons(activeLayout) {
    const layoutMap = {
        'forceDirected': 'layout-force',
        'hierarchical': 'layout-hierarchical',
        'radial': 'layout-radial'
    };

    for (const [layout, buttonId] of Object.entries(layoutMap)) {
        const button = document.getElementById(buttonId);
        if (button) {
            if (layout === activeLayout) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        }
    }
}

/**
 * Reset view to default zoom and center
 */
function resetView() {
    cy.fit();
    cy.center();
}

/**
 * Update statistics display
 * @param {Object} graphData - Graph data
 */
function updateStatistics(graphData) {
    const totalNodes = cy.nodes().length;
    const totalEdges = cy.edges().length;
    const cycleNodes = cy.nodes('[inCycle]').length;

    document.getElementById('stat-nodes').textContent = `Nodes: ${totalNodes}`;
    document.getElementById('stat-edges').textContent = `Edges: ${totalEdges}`;
    document.getElementById('stat-cycles').textContent = `Cycle Nodes: ${cycleNodes}`;
}

/**
 * Show tooltip
 * @param {string} id - Node/Edge ID
 * @param {string} title - Title
 * @param {number} x - X position
 * @param {number} y - Y position
 */
function showTooltip(id, title, x, y) {
    const tooltip = document.getElementById('tooltip');
    const node = cy.getElementById(id);
    const renderedPosition = node.renderedPosition();

    tooltip.innerHTML = `<strong>${id}</strong><br>${title}`;
    tooltip.style.left = (renderedPosition.x + 10) + 'px';
    tooltip.style.top = (renderedPosition.y + 10) + 'px';
    tooltip.classList.remove('hidden');
}

/**
 * Show edge tooltip
 * @param {string} title - Reference title
 * @param {string} type - Reference type
 * @param {number} x - X position
 * @param {number} y - Y position
 */
function showEdgeTooltip(title, type, x, y) {
    const tooltip = document.getElementById('tooltip');
    tooltip.innerHTML = `<strong>${type.toUpperCase()} Reference</strong><br>${title}`;
    tooltip.style.left = (x + 10) + 'px';
    tooltip.style.top = (y + 10) + 'px';
    tooltip.classList.remove('hidden');
}

/**
 * Hide tooltip
 */
function hideTooltip() {
    const tooltip = document.getElementById('tooltip');
    tooltip.classList.add('hidden');
}

/**
 * Show details panel for a node
 * @param {Object} node - Cytoscape node
 */
function showDetailsPanel(node) {
    const data = node.data();

    document.getElementById('detail-id').textContent = data.id;
    document.getElementById('detail-title').textContent = data.title || 'N/A';
    document.getElementById('detail-date').textContent = data.date || 'N/A';
    document.getElementById('detail-department').textContent = data.department || 'N/A';
    document.getElementById('detail-type').textContent = data.type || 'N/A';
    document.getElementById('detail-cycle').textContent = data.inCycle ? 'Yes' : 'No';

    // Outgoing references
    const outgoingEdges = node.connectedEdges('[source = "' + data.id + '"]');
    const referencesHtml = outgoingEdges.map(edge => {
        return `<div>${edge.data('refType').toUpperCase()}: ${edge.data('refTitle')}</div>`;
    }).join('');
    document.getElementById('detail-references').innerHTML = referencesHtml || 'None';

    // Incoming references
    const incomingEdges = node.connectedEdges('[target = "' + data.id + '"]');
    const incomingHtml = incomingEdges.map(edge => {
        return `<div>${edge.data('source')}</div>`;
    }).join('');
    document.getElementById('detail-incoming').innerHTML = incomingHtml || 'None';

    // Content summary
    const contentSummary = extractContentSummary(data.content, 300);
    document.getElementById('detail-content').textContent = contentSummary;

    // URL
    const urlElement = document.getElementById('detail-url');
    if (data.url && data.url.trim() !== '') {
        urlElement.href = data.url;
        urlElement.textContent = data.url;
        urlElement.style.display = 'inline';
    } else {
        urlElement.style.display = 'none';
    }

    // Show panel
    document.getElementById('details-panel').classList.remove('hidden');
}

/**
 * Hide details panel
 */
function hideDetailsPanel() {
    document.getElementById('details-panel').classList.add('hidden');
}

/**
 * Get Cytoscape instance
 * @returns {Object} - Cytoscape instance
 */
function getCytoscape() {
    return cy;
}
