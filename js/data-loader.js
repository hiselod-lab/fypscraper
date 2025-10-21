/**
 * Data Loader Module
 * Handles loading and parsing of JSON data files
 */

// File paths configuration
const DATA_FILES = {
    main: [
        'acd_results_with_pdf_circular_content.json',
        'bpd_results_with_pdf_circular_content.json',
        'bprd_results_with_pdf_circular_content.json',
        'bsd_results_with_pdf_circular_content.json',
        'bsrvd_results_with_pdf_circular_content.json'
    ],
    cache: 'circular_content_cache.json'
};

/**
 * Load a single JSON file with error handling
 * @param {string} url - File path
 * @returns {Promise<Object|null>} - Parsed JSON or null on error
 */
async function loadJSONFile(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        console.log(`✓ Loaded: ${url}`);
        return data;
    } catch (error) {
        console.warn(`✗ Failed to load: ${url} - ${error.message}`);
        return null;
    }
}

/**
 * Load all data files (main files + cache)
 * @returns {Promise<Object>} - Object containing loaded data
 */
async function loadDataFiles() {
    console.log('Loading data files...');

    // Load main files
    const mainFilePromises = DATA_FILES.main.map(file => loadJSONFile(file));
    const mainFilesData = await Promise.all(mainFilePromises);

    // Filter out null results (failed loads)
    const loadedMainFiles = mainFilesData.filter(data => data !== null);

    // Load cache file
    const cacheData = await loadJSONFile(DATA_FILES.cache);

    // Calculate loading statistics
    const loadedCount = loadedMainFiles.length;
    const totalCount = DATA_FILES.main.length;

    console.log(`\n=== Loading Summary ===`);
    console.log(`Loaded ${loadedCount} of ${totalCount} main files${cacheData ? ', plus cache' : ''}`);
    console.log(`======================\n`);

    // Update loading status in UI
    const loadingText = document.getElementById('loading-text');
    if (loadingText) {
        loadingText.textContent = `Loaded ${loadedCount} of ${totalCount} files${cacheData ? ' (+ cache)' : ''}`;
    }

    return {
        mainFiles: loadedMainFiles,
        cache: cacheData,
        stats: {
            loadedCount,
            totalCount,
            hasCache: cacheData !== null
        }
    };
}

/**
 * Extract year from date string (format: "Month DD, YYYY")
 * @param {string} dateString - Date string
 * @returns {number|null} - Extracted year or null
 */
function extractYearFromDate(dateString) {
    if (!dateString) return null;
    const match = dateString.match(/(\d{4})/);
    return match ? parseInt(match[1], 10) : null;
}

/**
 * Extract department from circular ID
 * @param {string} circularId - Circular ID
 * @returns {string} - Department code
 */
function extractDepartmentFromId(circularId) {
    if (!circularId) return 'Other';

    const match = circularId.match(/^([A-Z&]+)\s/);
    if (match) {
        const dept = match[1];
        // Normalize department variations
        if (dept.includes('AC') && dept.includes('MFD')) return 'AC&MFD';
        if (dept === 'ACMFD') return 'AC&MFD';
        return dept;
    }
    return 'Other';
}

/**
 * Normalize circular title for matching
 * Based on circular_content_extractor.py logic (lines 271-356)
 * @param {string} title - Circular title
 * @returns {string} - Normalized title
 */
function normalizeTitle(title) {
    if (!title) return '';

    let normalized = title.toLowerCase();

    // Remove leading zeros from numbers
    normalized = normalized.replace(/\b0+(\d)/g, '$1');

    // Standardize "no." variations
    normalized = normalized.replace(/no\.\s*/gi, 'no ');

    // Remove extra whitespace
    normalized = normalized.replace(/\s+/g, ' ').trim();

    return normalized;
}

/**
 * Generate a unique ID for a node
 * @param {string} id - Original ID
 * @param {string} url - URL (fallback)
 * @param {string} title - Title (fallback)
 * @returns {string} - Unique ID
 */
function generateNodeId(id, url, title) {
    if (id) return id;
    if (url) return `url_${url}`;
    if (title) return `title_${title}`;
    return `node_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Extract content summary from content array
 * @param {Array} content - Content array
 * @param {number} maxLength - Maximum length
 * @returns {string} - Content summary
 */
function extractContentSummary(content, maxLength = 300) {
    if (!content || !Array.isArray(content)) return 'No content available';

    let summary = '';

    for (const item of content) {
        if (item.type === 'content' && item.text) {
            summary += item.text + ' ';
        } else if (item.type === 'hierarchical_content' && item.text) {
            summary += item.text + ' ';
        } else if (item.type === 'list' && item.items) {
            summary += item.items.join(', ') + ' ';
        }

        if (summary.length > maxLength) break;
    }

    return summary.substring(0, maxLength).trim() + (summary.length > maxLength ? '...' : '');
}
