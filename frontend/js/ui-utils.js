/**
 * LIZZY - UI Utilities Module
 * Common UI helper functions for frontend
 */

/**
 * Show a toast message to the user
 * @param {string} text - Message text
 * @param {string} type - Message type: 'success', 'error', 'info'
 * @param {number} duration - How long to show message (ms). 0 = don't auto-hide
 */
function showMessage(text, type = 'info', duration = 4000) {
    const container = document.getElementById('message-container');
    if (!container) {
        console.warn('Message container not found. Add <div id="message-container"></div> to your HTML');
        return;
    }

    const messageClass = type === 'success' ? 'message-success' :
                        type === 'error' ? 'message-error' : 'message-info';

    container.innerHTML = `<div class="message ${messageClass}">${escapeHtml(text)}</div>`;

    if (duration > 0 && type === 'success') {
        setTimeout(() => {
            container.innerHTML = '';
        }, duration);
    }
}

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML string
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get URL parameter value
 * @param {string} name - Parameter name
 * @returns {string|null} Parameter value or null
 */
function getUrlParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

/**
 * Get current project from URL or localStorage
 * @returns {string|null} Project name or null
 */
function getCurrentProject() {
    return getUrlParam('project') || localStorage.getItem('currentProject');
}

/**
 * Set current project in localStorage
 * @param {string} projectName - Project name to set
 */
function setCurrentProject(projectName) {
    if (projectName) {
        localStorage.setItem('currentProject', projectName);
    } else {
        localStorage.removeItem('currentProject');
    }
}

/**
 * Redirect to a page with optional query parameters
 * @param {string} path - Path to redirect to (e.g., '/brainstorm')
 * @param {Object} params - Query parameters as key-value pairs
 */
function redirectTo(path, params = {}) {
    const queryString = Object.keys(params)
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        .join('&');

    const url = queryString ? `${path}?${queryString}` : path;
    window.location.href = url;
}

/**
 * Show loading spinner
 * @param {string} elementId - ID of element to show spinner in
 * @param {string} message - Optional loading message
 */
function showLoading(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.innerHTML = `
        <div class="loading text-center">
            <div class="spinner"></div>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

/**
 * Hide loading spinner
 * @param {string} elementId - ID of element containing spinner
 */
function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    element.innerHTML = '';
}

/**
 * Format date for display
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text with ellipsis
 */
function truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Confirm action with user
 * @param {string} message - Confirmation message
 * @returns {boolean} True if user confirmed
 */
function confirmAction(message) {
    return confirm(message);
}

/**
 * Debounce function to limit rate of function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Poll a function at regular intervals until condition is met
 * @param {Function} checkFn - Async function to check condition
 * @param {number} interval - Interval in milliseconds
 * @param {number} maxAttempts - Maximum number of attempts (0 = infinite)
 * @returns {Promise} Resolves when condition is met or max attempts reached
 */
async function poll(checkFn, interval = 3000, maxAttempts = 0) {
    let attempts = 0;

    return new Promise((resolve, reject) => {
        const intervalId = setInterval(async () => {
            attempts++;

            try {
                const result = await checkFn();

                if (result) {
                    clearInterval(intervalId);
                    resolve(result);
                }

                if (maxAttempts > 0 && attempts >= maxAttempts) {
                    clearInterval(intervalId);
                    reject(new Error('Max polling attempts reached'));
                }
            } catch (error) {
                clearInterval(intervalId);
                reject(error);
            }
        }, interval);
    });
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} True if successful
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        return false;
    }
}

/**
 * Download text as file
 * @param {string} content - File content
 * @param {string} filename - Name of file to download
 * @param {string} mimeType - MIME type (default: text/plain)
 */
function downloadAsFile(content, filename, mimeType = 'text/plain') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Export all utilities for use in HTML scripts
if (typeof window !== 'undefined') {
    window.UIUtils = {
        showMessage,
        escapeHtml,
        getUrlParam,
        getCurrentProject,
        setCurrentProject,
        redirectTo,
        showLoading,
        hideLoading,
        formatDate,
        truncateText,
        confirmAction,
        debounce,
        poll,
        copyToClipboard,
        downloadAsFile
    };

    // Also export individual functions for convenience
    window.showMessage = showMessage;
    window.escapeHtml = escapeHtml;
    window.getUrlParam = getUrlParam;
    window.getCurrentProject = getCurrentProject;
    window.setCurrentProject = setCurrentProject;
}
