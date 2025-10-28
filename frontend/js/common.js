/**
 * Common utilities shared across all Lizzy 2.0 pages
 */

// ===== PROJECT MANAGEMENT =====

/**
 * Get current project from localStorage or URL params
 * @param {URLSearchParams} urlParams - Optional URL parameters to check
 * @returns {string|null} Current project name
 */
function getCurrentProject(urlParams = null) {
    if (urlParams) {
        const projectFromUrl = urlParams.get('project');
        if (projectFromUrl) {
            localStorage.setItem('currentProject', projectFromUrl);
            return projectFromUrl;
        }
    }
    return localStorage.getItem('currentProject');
}

/**
 * Update header project name display
 * @param {string} projectName - Project name to display (optional, reads from localStorage if not provided)
 */
async function updateHeaderProjectName(projectName = null) {
    const headerDisplay = document.getElementById('header-project-name');
    if (!headerDisplay) return;

    const project = projectName || localStorage.getItem('currentProject');
    if (project) {
        // Fetch display name from API
        try {
            const response = await fetch(`/api/project/${project}`);
            const data = await response.json();
            if (data && data.project && data.project.name) {
                headerDisplay.textContent = data.project.name;
            } else {
                // Fallback: convert underscores to spaces and title case
                headerDisplay.textContent = project.replace(/_/g, ' ');
            }
        } catch (error) {
            // Fallback on error
            headerDisplay.textContent = project.replace(/_/g, ' ');
        }
    } else {
        headerDisplay.textContent = 'No project selected';
    }
}

// ===== MESSAGE DISPLAY =====

/**
 * Show a message to the user
 * @param {string} text - Message text
 * @param {string} type - Message type: 'success', 'error', 'info', 'warning'
 * @param {number} duration - Auto-dismiss duration in ms (0 = no auto-dismiss)
 */
function showMessage(text, type = 'info', duration = 4000) {
    const container = document.getElementById('message-container');
    if (!container) {
        console.warn('Message container not found');
        return;
    }

    const messageId = 'msg-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message-alert ${type}`;
    messageDiv.innerHTML = escapeHtml(text);

    container.appendChild(messageDiv);

    // Auto-dismiss for success messages or if duration specified
    if (duration > 0 && (type === 'success' || type === 'info')) {
        setTimeout(() => {
            const msg = document.getElementById(messageId);
            if (msg) {
                msg.style.opacity = '0';
                setTimeout(() => msg.remove(), 300);
            }
        }, duration);
    }

    // Add close button for persistent messages
    if (duration === 0 || type === 'error' || type === 'warning') {
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '×';
        closeBtn.className = 'message-close';
        closeBtn.onclick = () => {
            messageDiv.style.opacity = '0';
            setTimeout(() => messageDiv.remove(), 300);
        };
        messageDiv.appendChild(closeBtn);
    }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== PROGRESS BAR =====

/**
 * Update a progress bar
 * @param {string} containerId - ID of the progress bar container
 * @param {number} completed - Number of completed items
 * @param {number} total - Total number of items
 * @param {string} label - Optional label (defaults to "X/Y scenes")
 */
function updateProgressBar(containerId, completed, total, label = null) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    const progressFill = container.querySelector('.progress-fill');

    if (progressFill) {
        progressFill.style.width = percentage + '%';
    }

    const labelText = label || `${completed}/${total} scenes`;
    container.setAttribute('data-progress', labelText);
}

// ===== BATCH OPERATIONS =====

/**
 * Batch operation state manager
 */
const BatchOperation = {
    activeOperations: {},

    start(operationId, totalItems) {
        this.activeOperations[operationId] = {
            total: totalItems,
            completed: 0,
            failed: 0,
            currentItem: null,
            startTime: Date.now(),
            cancelled: false
        };
    },

    update(operationId, updates) {
        if (this.activeOperations[operationId]) {
            Object.assign(this.activeOperations[operationId], updates);
        }
    },

    cancel(operationId) {
        if (this.activeOperations[operationId]) {
            this.activeOperations[operationId].cancelled = true;
        }
    },

    isCancelled(operationId) {
        return this.activeOperations[operationId]?.cancelled || false;
    },

    getProgress(operationId) {
        return this.activeOperations[operationId] || null;
    },

    complete(operationId) {
        delete this.activeOperations[operationId];
    },

    getEstimatedTimeRemaining(operationId) {
        const op = this.activeOperations[operationId];
        if (!op || op.completed === 0) return null;

        const elapsed = Date.now() - op.startTime;
        const avgTimePerItem = elapsed / op.completed;
        const remaining = op.total - op.completed;
        return Math.round((avgTimePerItem * remaining) / 1000); // seconds
    }
};

// ===== COST ESTIMATION =====

/**
 * Estimate cost for operations
 * @param {number} sceneCount - Number of scenes
 * @param {string} operationType - 'brainstorm' or 'write'
 * @returns {object} Cost estimate with low, high, and avg
 */
function estimateCost(sceneCount, operationType = 'brainstorm') {
    const costs = {
        brainstorm: { low: 0.008, avg: 0.010, high: 0.012 }, // per scene
        write: { low: 0.015, avg: 0.020, high: 0.025 }      // per scene
    };

    const cost = costs[operationType] || costs.brainstorm;

    return {
        low: (cost.low * sceneCount).toFixed(2),
        avg: (cost.avg * sceneCount).toFixed(2),
        high: (cost.high * sceneCount).toFixed(2)
    };
}

/**
 * Format cost estimate for display
 * @param {number} sceneCount - Number of scenes
 * @param {string} operationType - 'brainstorm' or 'write'
 * @returns {string} Formatted cost string
 */
function formatCostEstimate(sceneCount, operationType = 'brainstorm') {
    const estimate = estimateCost(sceneCount, operationType);
    return `$${estimate.avg} (range: $${estimate.low}-$${estimate.high})`;
}

// ===== STATUS BADGES =====

/**
 * Create a status badge HTML
 * @param {string} status - Status type
 * @param {string} text - Badge text
 * @returns {string} HTML string for badge
 */
function createStatusBadge(status, text) {
    const badges = {
        success: 'status-success',
        pending: 'status-pending',
        error: 'status-error',
        processing: 'status-processing'
    };

    const className = badges[status] || 'status-pending';
    return `<span class="status ${className}">${escapeHtml(text)}</span>`;
}

// ===== TABLE UTILITIES =====

/**
 * Filter table rows by act number
 * @param {string} tableBodyId - ID of table tbody
 * @param {string} filterValue - 'all' or act number
 * @param {string} actAttribute - Data attribute name (default: 'data-act')
 */
function filterTableByAct(tableBodyId, filterValue, actAttribute = 'data-act') {
    const tbody = document.getElementById(tableBodyId);
    if (!tbody) return;

    const rows = tbody.getElementsByTagName('tr');
    let visibleCount = 0;

    Array.from(rows).forEach(row => {
        if (filterValue === 'all') {
            row.style.display = '';
            visibleCount++;
        } else {
            const rowAct = row.getAttribute(actAttribute);
            if (rowAct === filterValue) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        }
    });

    return visibleCount;
}

// ===== NAVIGATION =====

/**
 * Navigate to a page with current project in query params
 * @param {string} path - Path to navigate to
 * @param {object} extraParams - Additional query parameters
 */
function navigateWithProject(path, extraParams = {}) {
    const currentProject = localStorage.getItem('currentProject');
    if (!currentProject && path !== '/' && path !== '/manager') {
        showMessage('⚠️ Please select a project from the dropdown first!', 'warning', 3000);
        setTimeout(() => window.location.href = '/', 2000);
        return;
    }

    const params = new URLSearchParams();
    if (currentProject) {
        params.set('project', currentProject);
    }

    Object.entries(extraParams).forEach(([key, value]) => {
        params.set(key, value);
    });

    const url = params.toString() ? `${path}?${params.toString()}` : path;
    window.location.href = url;
}

// ===== FORMAT UTILITIES =====

/**
 * Format timestamp for display
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted date/time
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Format word count for display
 * @param {number} wordCount - Number of words
 * @returns {string} Formatted word count
 */
function formatWordCount(wordCount) {
    if (!wordCount) return '0 words';
    if (wordCount >= 1000) {
        return `${(wordCount / 1000).toFixed(1)}k words`;
    }
    return `${wordCount} words`;
}

/**
 * Estimate page count from word count (screenplay format: ~250 words/page)
 * @param {number} wordCount - Number of words
 * @returns {string} Formatted page count
 */
function estimatePageCount(wordCount) {
    if (!wordCount) return '0 pages';
    const pages = Math.ceil(wordCount / 250);
    return `~${pages} page${pages !== 1 ? 's' : ''}`;
}

/**
 * Format time duration in seconds to readable string
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration
 */
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

// ===== MODAL UTILITIES =====

/**
 * Show a modal
 * @param {string} modalId - ID of modal element
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

/**
 * Hide a modal
 * @param {string} modalId - ID of modal element
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// ===== API UTILITIES =====

/**
 * Make an API call with error handling
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<object>} API response data
 */
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);

        // Try to parse JSON response
        let data;
        try {
            data = await response.json();
        } catch (parseError) {
            // If JSON parse fails and response is not OK, throw generic error
            if (!response.ok) {
                throw new Error(`Server error (${response.status}): ${response.statusText}`);
            }
            throw new Error('Invalid server response: Unable to parse JSON');
        }

        // Handle HTTP errors with detailed JSON error messages
        if (!response.ok) {
            // Extract error from various response formats
            const errorMsg = data.detail || data.error || data.message || response.statusText;
            throw new Error(`${errorMsg} (HTTP ${response.status})`);
        }

        // Handle success: false pattern in JSON responses
        if (data.success === false) {
            const errorMsg = data.error || data.message || 'Operation failed';
            throw new Error(errorMsg);
        }

        return data;
    } catch (error) {
        // Log full error details for debugging
        console.error('API call failed:', {
            url,
            method: options.method || 'GET',
            error: error.message,
            stack: error.stack
        });
        throw error;
    }
}

/**
 * Make an API call with automatic retry logic and exponential backoff
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @param {number} maxRetries - Maximum number of retry attempts (default: 3)
 * @returns {Promise<object>} API response data
 */
async function apiCallWithRetry(url, options = {}, maxRetries = 3) {
    let lastError;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            // Use the standard apiCall function
            return await apiCall(url, options);
        } catch (error) {
            lastError = error;

            // Check if error is retriable
            const isRetriable = isRetriableError(error);
            const isLastAttempt = attempt === maxRetries;

            // Don't retry on non-retriable errors or last attempt
            if (!isRetriable || isLastAttempt) {
                throw error;
            }

            // Calculate exponential backoff delay: 1s, 2s, 4s, 8s
            const delay = Math.pow(2, attempt) * 1000;

            console.warn(`API call failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms...`, {
                url,
                error: error.message
            });

            // Wait before retrying
            await sleep(delay);
        }
    }

    // This should never be reached, but just in case
    throw lastError;
}

/**
 * Check if an error is retriable (network errors, 5xx server errors)
 * @param {Error} error - Error object
 * @returns {boolean} True if error should be retried
 */
function isRetriableError(error) {
    const message = error.message.toLowerCase();

    // Network errors
    if (message.includes('network') ||
        message.includes('fetch') ||
        message.includes('connection') ||
        message.includes('timeout')) {
        return true;
    }

    // 5xx server errors (temporary server issues)
    if (message.match(/http 5\d\d/)) {
        return true;
    }

    // Don't retry 4xx client errors (bad request, validation, etc.)
    if (message.match(/http 4\d\d/)) {
        return false;
    }

    // By default, don't retry unknown errors
    return false;
}

/**
 * Sleep for a specified duration
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise<void>}
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ===== LOADING STATES =====

/**
 * Show loading indicator on an element
 * @param {HTMLElement|string} element - Element or ID to show loading on
 * @param {string} message - Optional loading message
 */
function showLoading(element, message = 'Loading...') {
    const el = typeof element === 'string' ? document.getElementById(element) : element;
    if (!el) return;

    el.dataset.originalContent = el.innerHTML;
    el.dataset.originalDisabled = el.disabled;
    el.disabled = true;
    el.style.opacity = '0.6';
    el.style.cursor = 'wait';

    if (el.tagName === 'BUTTON') {
        el.innerHTML = `<span style="display: inline-flex; align-items: center; gap: 8px;"><span class="spinner" style="width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></span>${message}</span>`;
    }
}

/**
 * Hide loading indicator and restore original content
 * @param {HTMLElement|string} element - Element or ID to hide loading from
 */
function hideLoading(element) {
    const el = typeof element === 'string' ? document.getElementById(element) : element;
    if (!el || !el.dataset.originalContent) return;

    el.innerHTML = el.dataset.originalContent;
    el.disabled = el.dataset.originalDisabled === 'true';
    el.style.opacity = '';
    el.style.cursor = '';

    delete el.dataset.originalContent;
    delete el.dataset.originalDisabled;
}

// ===== INITIALIZATION =====

// Auto-update header on page load if element exists
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('header-project-name')) {
        updateHeaderProjectName();
    }
});
