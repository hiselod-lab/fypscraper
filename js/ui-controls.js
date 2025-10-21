/**
 * UI Controls Module
 * Handles control panel interactions and event wiring
 */

/**
 * Initialize all UI controls
 */
function initializeControls() {
    console.log('Initializing UI controls...');

    // Layout controls
    setupLayoutControls();

    // Department filters
    initializeDepartmentFilters();

    // Year range filters
    initializeYearFilters();

    // Search controls
    setupSearchControls();

    // Display options
    setupDisplayOptions();

    // View controls
    setupViewControls();

    // Details panel controls
    setupDetailsPanelControls();

    console.log('UI controls initialized');
}

/**
 * Setup layout controls
 */
function setupLayoutControls() {
    document.getElementById('layout-force').addEventListener('click', () => {
        switchLayout('forceDirected');
    });

    document.getElementById('layout-hierarchical').addEventListener('click', () => {
        switchLayout('hierarchical');
    });

    document.getElementById('layout-radial').addEventListener('click', () => {
        switchLayout('radial');
    });
}

/**
 * Setup search controls
 */
function setupSearchControls() {
    const searchInput = document.getElementById('search-input');
    const searchClear = document.getElementById('search-clear');

    // Debounce search input
    let searchTimeout;
    searchInput.addEventListener('input', (event) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            onSearchInput(event);
        }, 300);
    });

    // Clear button
    searchClear.addEventListener('click', () => {
        clearSearch();
    });

    // Enter key to search
    searchInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            clearTimeout(searchTimeout);
            onSearchInput(event);
        }
    });
}

/**
 * Setup display options
 */
function setupDisplayOptions() {
    document.getElementById('show-cycles-only').addEventListener('change', (event) => {
        onDisplayOptionChange('showCyclesOnly', event.target.checked);
    });

    document.getElementById('show-labels').addEventListener('change', (event) => {
        onDisplayOptionChange('showLabels', event.target.checked);
    });

    document.getElementById('show-isolated').addEventListener('change', (event) => {
        onDisplayOptionChange('showIsolated', event.target.checked);
    });
}

/**
 * Setup view controls
 */
function setupViewControls() {
    document.getElementById('reset-view').addEventListener('click', () => {
        resetView();
    });

    document.getElementById('reset-filters').addEventListener('click', () => {
        resetFilters();
    });
}

/**
 * Setup details panel controls
 */
function setupDetailsPanelControls() {
    document.getElementById('close-details').addEventListener('click', () => {
        hideDetailsPanel();

        // Clear highlighting
        const cy = getCytoscape();
        if (cy) {
            cy.elements().removeClass('dimmed highlighted');
            cy.edges().style('width', edge => edge.data('isCycleEdge') ? 3 : 2);
        }
    });
}

/**
 * Show error message to user
 * @param {string} message - Error message
 */
function showError(message) {
    const loadingText = document.getElementById('loading-text');
    const loadingSpinner = document.querySelector('.loading-spinner');

    if (loadingText) {
        loadingText.textContent = message;
        loadingText.style.color = '#cc0000';
    }

    if (loadingSpinner) {
        loadingSpinner.style.display = 'none';
    }

    console.error(message);
}

/**
 * Show success message to user
 * @param {string} message - Success message
 */
function showSuccess(message) {
    const loadingText = document.getElementById('loading-text');

    if (loadingText) {
        loadingText.textContent = message;
        loadingText.style.color = '#009900';
    }

    console.log(message);
}
