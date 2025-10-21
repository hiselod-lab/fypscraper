/**
 * Filters Module
 * Handles filtering logic for department, year, search, and display options
 */

// Active filters state
let activeFilters = {
    departments: new Set(),
    yearMin: 2000,
    yearMax: 2025,
    searchQuery: '',
    showCyclesOnly: false,
    showLabels: false,
    showIsolated: true
};

/**
 * Initialize department filters
 */
function initializeDepartmentFilters() {
    const cy = getCytoscape();
    if (!cy) return;

    // Get all unique departments
    const departments = new Set();
    cy.nodes().forEach(node => {
        const dept = node.data('department');
        if (dept) departments.add(dept);
    });

    // Sort departments
    const sortedDepartments = Array.from(departments).sort();

    // Create checkbox for each department
    const container = document.getElementById('department-filters');
    container.innerHTML = '';

    for (const dept of sortedDepartments) {
        const count = cy.nodes(`[department = "${dept}"]`).length;

        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = dept;
        checkbox.checked = true;
        checkbox.addEventListener('change', onDepartmentFilterChange);

        const span = document.createElement('span');
        span.textContent = `${dept} (${count})`;

        label.appendChild(checkbox);
        label.appendChild(span);
        container.appendChild(label);

        // Add to active filters
        activeFilters.departments.add(dept);
    }

    // Load saved filters from localStorage
    loadFilterState();
}

/**
 * Initialize year range filters
 */
function initializeYearFilters() {
    const cy = getCytoscape();
    if (!cy) return;

    // Find min and max years in data
    let minYear = 3000;
    let maxYear = 1000;

    cy.nodes().forEach(node => {
        const year = node.data('year');
        if (year) {
            minYear = Math.min(minYear, year);
            maxYear = Math.max(maxYear, year);
        }
    });

    // Set defaults if no years found
    if (minYear === 3000) minYear = 2000;
    if (maxYear === 1000) maxYear = 2025;

    // Update slider ranges
    const yearMinSlider = document.getElementById('year-min');
    const yearMaxSlider = document.getElementById('year-max');

    yearMinSlider.min = minYear;
    yearMinSlider.max = maxYear;
    yearMinSlider.value = minYear;

    yearMaxSlider.min = minYear;
    yearMaxSlider.max = maxYear;
    yearMaxSlider.value = maxYear;

    activeFilters.yearMin = minYear;
    activeFilters.yearMax = maxYear;

    updateYearDisplay();

    // Add event listeners
    yearMinSlider.addEventListener('input', onYearFilterChange);
    yearMaxSlider.addEventListener('input', onYearFilterChange);
}

/**
 * Update year display text
 */
function updateYearDisplay() {
    document.getElementById('year-display').textContent =
        `Selected: ${activeFilters.yearMin} - ${activeFilters.yearMax}`;
}

/**
 * Handle department filter change
 */
function onDepartmentFilterChange(event) {
    const dept = event.target.value;

    if (event.target.checked) {
        activeFilters.departments.add(dept);
    } else {
        activeFilters.departments.delete(dept);
    }

    applyFilters();
    saveFilterState();
}

/**
 * Handle year filter change
 */
function onYearFilterChange(event) {
    const yearMin = parseInt(document.getElementById('year-min').value);
    const yearMax = parseInt(document.getElementById('year-max').value);

    // Ensure min <= max
    if (yearMin > yearMax) {
        if (event.target.id === 'year-min') {
            document.getElementById('year-min').value = yearMax;
            activeFilters.yearMin = yearMax;
        } else {
            document.getElementById('year-max').value = yearMin;
            activeFilters.yearMax = yearMin;
        }
    } else {
        activeFilters.yearMin = yearMin;
        activeFilters.yearMax = yearMax;
    }

    updateYearDisplay();
    applyFilters();
    saveFilterState();
}

/**
 * Handle search input
 */
function onSearchInput(event) {
    activeFilters.searchQuery = event.target.value.toLowerCase().trim();
    applyFilters();
}

/**
 * Clear search
 */
function clearSearch() {
    document.getElementById('search-input').value = '';
    activeFilters.searchQuery = '';
    applyFilters();
}

/**
 * Handle display option change
 * @param {string} option - Option name
 * @param {boolean} checked - Checked state
 */
function onDisplayOptionChange(option, checked) {
    activeFilters[option] = checked;
    applyFilters();
    saveFilterState();
}

/**
 * Apply all filters to the graph
 */
function applyFilters() {
    const cy = getCytoscape();
    if (!cy) return;

    // Reset all elements
    cy.elements().removeClass('hidden dimmed');

    // Filter by department
    cy.nodes().forEach(node => {
        const dept = node.data('department');
        if (!activeFilters.departments.has(dept)) {
            node.addClass('hidden');
        }
    });

    // Filter by year
    cy.nodes().forEach(node => {
        const year = node.data('year');
        if (year && (year < activeFilters.yearMin || year > activeFilters.yearMax)) {
            node.addClass('hidden');
        }
    });

    // Filter by search query
    if (activeFilters.searchQuery) {
        const matchingNodes = cy.nodes().filter(node => {
            const id = (node.data('id') || '').toLowerCase();
            const title = (node.data('title') || '').toLowerCase();
            return id.includes(activeFilters.searchQuery) || title.includes(activeFilters.searchQuery);
        });

        cy.nodes().forEach(node => {
            if (!matchingNodes.contains(node) && !node.hasClass('hidden')) {
                node.addClass('dimmed');
            }
        });

        // Update search results count
        document.getElementById('search-results').textContent =
            matchingNodes.length > 0 ? `Found ${matchingNodes.length} circular(s)` : 'No matches found';
    } else {
        document.getElementById('search-results').textContent = '';
    }

    // Show cycles only
    if (activeFilters.showCyclesOnly) {
        cy.nodes().forEach(node => {
            if (!node.data('inCycle') && !node.hasClass('hidden')) {
                node.addClass('hidden');
            }
        });
    }

    // Show/hide isolated nodes
    if (!activeFilters.showIsolated) {
        cy.nodes().forEach(node => {
            if (node.degree() === 0 && !node.hasClass('hidden')) {
                node.addClass('hidden');
            }
        });
    }

    // Hide edges if source or target is hidden
    cy.edges().forEach(edge => {
        const source = edge.source();
        const target = edge.target();

        if (source.hasClass('hidden') || target.hasClass('hidden')) {
            edge.addClass('hidden');
        }
    });

    // Show/hide labels
    if (activeFilters.showLabels) {
        cy.nodes().style('label', node => node.data('id'));
    } else {
        cy.nodes().style('label', '');
    }

    // Update statistics
    updateFilteredStatistics();
}

/**
 * Update statistics for filtered graph
 */
function updateFilteredStatistics() {
    const cy = getCytoscape();
    if (!cy) return;

    const visibleNodes = cy.nodes(':visible').not('.hidden').length;
    const visibleEdges = cy.edges(':visible').not('.hidden').length;
    const cycleNodes = cy.nodes('[inCycle]:visible').not('.hidden').length;

    document.getElementById('stat-nodes').textContent = `Nodes: ${visibleNodes}`;
    document.getElementById('stat-edges').textContent = `Edges: ${visibleEdges}`;
    document.getElementById('stat-cycles').textContent = `Cycle Nodes: ${cycleNodes}`;
}

/**
 * Reset all filters to defaults
 */
function resetFilters() {
    const cy = getCytoscape();
    if (!cy) return;

    // Reset department filters
    document.querySelectorAll('#department-filters input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = true;
        activeFilters.departments.add(checkbox.value);
    });

    // Reset year filters
    const yearMinSlider = document.getElementById('year-min');
    const yearMaxSlider = document.getElementById('year-max');
    yearMinSlider.value = yearMinSlider.min;
    yearMaxSlider.value = yearMaxSlider.max;
    activeFilters.yearMin = parseInt(yearMinSlider.min);
    activeFilters.yearMax = parseInt(yearMaxSlider.max);
    updateYearDisplay();

    // Reset search
    document.getElementById('search-input').value = '';
    activeFilters.searchQuery = '';

    // Reset display options
    document.getElementById('show-cycles-only').checked = false;
    activeFilters.showCyclesOnly = false;

    document.getElementById('show-labels').checked = false;
    activeFilters.showLabels = false;

    document.getElementById('show-isolated').checked = true;
    activeFilters.showIsolated = true;

    // Apply filters
    applyFilters();

    // Clear saved state
    localStorage.removeItem('filterState');
}

/**
 * Save filter state to localStorage
 */
function saveFilterState() {
    const state = {
        departments: Array.from(activeFilters.departments),
        yearMin: activeFilters.yearMin,
        yearMax: activeFilters.yearMax,
        showCyclesOnly: activeFilters.showCyclesOnly,
        showLabels: activeFilters.showLabels,
        showIsolated: activeFilters.showIsolated
    };

    localStorage.setItem('filterState', JSON.stringify(state));
}

/**
 * Load filter state from localStorage
 */
function loadFilterState() {
    const saved = localStorage.getItem('filterState');
    if (!saved) return;

    try {
        const state = JSON.parse(saved);

        // Restore department filters
        if (state.departments) {
            activeFilters.departments = new Set(state.departments);
            document.querySelectorAll('#department-filters input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = activeFilters.departments.has(checkbox.value);
            });
        }

        // Restore year filters
        if (state.yearMin !== undefined && state.yearMax !== undefined) {
            document.getElementById('year-min').value = state.yearMin;
            document.getElementById('year-max').value = state.yearMax;
            activeFilters.yearMin = state.yearMin;
            activeFilters.yearMax = state.yearMax;
            updateYearDisplay();
        }

        // Restore display options
        if (state.showCyclesOnly !== undefined) {
            document.getElementById('show-cycles-only').checked = state.showCyclesOnly;
            activeFilters.showCyclesOnly = state.showCyclesOnly;
        }

        if (state.showLabels !== undefined) {
            document.getElementById('show-labels').checked = state.showLabels;
            activeFilters.showLabels = state.showLabels;
        }

        if (state.showIsolated !== undefined) {
            document.getElementById('show-isolated').checked = state.showIsolated;
            activeFilters.showIsolated = state.showIsolated;
        }

        // Apply restored filters
        applyFilters();

    } catch (error) {
        console.error('Error loading filter state:', error);
    }
}
