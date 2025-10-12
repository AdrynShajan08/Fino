/**
 * API Client for making HTTP requests
 */
class ApiClient {
    /**
     * Make a request to the API
     * @param {string} url - The URL to request
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} Response data
     */
    static async request(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            showToast(error.message, 'danger');
            throw error;
        }
    }
    
    /**
     * Make a GET request
     * @param {string} url - The URL to request
     * @returns {Promise<Object>} Response data
     */
    static async get(url) {
        return this.request(url, { method: 'GET' });
    }
    
    /**
     * Make a POST request
     * @param {string} url - The URL to request
     * @param {Object} data - Data to send
     * @returns {Promise<Object>} Response data
     */
    static async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * Make a DELETE request
     * @param {string} url - The URL to request
     * @returns {Promise<Object>} Response data
     */
    static async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
}

/**
 * Debounce function to limit execution rate
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
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type (success, danger, warning, info)
 */
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3 fade show`;
    toast.style.zIndex = '9999';
    toast.style.minWidth = '250px';
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
    }, 3000);
}

/**
 * Format currency
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    return `₹${parseFloat(amount).toFixed(2)}`;
}

/**
 * Format date to YYYY-MM-DD
 * @param {Date|string} date - Date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    if (!date) return '';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Get today's date in YYYY-MM-DD format
 * @returns {string} Today's date
 */
function getTodayDate() {
    return formatDate(new Date());
}

/**
 * Confirm dialog wrapper
 * @param {string} message - Confirmation message
 * @returns {Promise<boolean>} User's confirmation
 */
async function confirmAction(message) {
    return confirm(message);
}

/**
 * Broadcast channel for cross-tab communication
 */
const financeChannel = new BroadcastChannel('finance_updates');

/**
 * Broadcast update to other tabs
 * @param {string} type - Type of update (expense, investment)
 */
function broadcastUpdate(type = 'general') {
    financeChannel.postMessage({ type, timestamp: Date.now() });
}

/**
 * Listen for updates from other tabs
 * @param {Function} callback - Callback function to execute on update
 */
function onUpdate(callback) {
    financeChannel.onmessage = (event) => {
        console.log('Received update:', event.data);
        callback(event.data);
    };
}

/**
 * Form data to object converter
 * @param {FormData} formData - Form data to convert
 * @returns {Object} Plain object
 */
function formDataToObject(formData) {
    const obj = {};
    for (const [key, value] of formData.entries()) {
        obj[key] = value;
    }
    return obj;
}

/**
 * Validate form inputs
 * @param {HTMLFormElement} form - Form to validate
 * @returns {boolean} Whether form is valid
 */
function validateForm(form) {
    if (!form.checkValidity()) {
        form.reportValidity();
        return false;
    }
    return true;
}