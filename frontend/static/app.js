/**
 * Eigencore ID - Frontend Authentication
 * Connects to the Eigencore API for auth operations
 */

// Configuration - will be replaced by environment in production
const CONFIG = {
    // API base URL - same origin in production, or override for dev
    apiUrl: window.EIGENCORE_API_URL || '',
    
    // OAuth redirect handling
    oauthRedirect: window.location.origin + '/auth/callback'
};

// DOM Elements
const elements = {
    tabs: document.querySelectorAll('.tab'),
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    loginError: document.getElementById('login-error'),
    registerError: document.getElementById('register-error'),
    oauthButtons: document.querySelectorAll('.btn-oauth'),
    modal: document.getElementById('success-modal'),
    modalClose: document.getElementById('modal-close'),
    userInfo: document.getElementById('user-info'),
    successMessage: document.getElementById('success-message')
};

// State
let currentTab = 'login';

// ==========================================================================
// Tab Switching
// ==========================================================================

function switchTab(tab) {
    currentTab = tab;
    
    elements.tabs.forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    
    elements.loginForm.classList.toggle('active', tab === 'login');
    elements.registerForm.classList.toggle('active', tab === 'register');
    
    // Clear errors when switching
    hideError('login');
    hideError('register');
}

elements.tabs.forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
});

// ==========================================================================
// Error Handling
// ==========================================================================

function showError(form, message) {
    const errorEl = form === 'login' ? elements.loginError : elements.registerError;
    errorEl.textContent = message;
    errorEl.classList.add('visible');
}

function hideError(form) {
    const errorEl = form === 'login' ? elements.loginError : elements.registerError;
    errorEl.classList.remove('visible');
}

// ==========================================================================
// API Calls
// ==========================================================================

async function apiCall(endpoint, options = {}) {
    const url = CONFIG.apiUrl + endpoint;
    
    const defaults = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    // Add auth token if available
    const token = localStorage.getItem('eigencore_token');
    if (token) {
        defaults.headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, { ...defaults, ...options });
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.detail || 'An error occurred');
    }
    
    return data;
}

// ==========================================================================
// Authentication
// ==========================================================================

async function login(email, password) {
    // API expects form data for OAuth2 password grant
    const formData = new URLSearchParams();
    formData.append('username', email);  // OAuth2 spec uses 'username'
    formData.append('password', password);
    
    const response = await fetch(CONFIG.apiUrl + '/api/v1/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
    }
    
    return data;
}

async function register(email, username, password) {
    return apiCall('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, username, password })
    });
}

async function getCurrentUser() {
    return apiCall('/api/v1/auth/me');
}

// ==========================================================================
// Form Handlers
// ==========================================================================

function setLoading(form, loading) {
    const btn = form.querySelector('.btn-primary');
    btn.classList.toggle('loading', loading);
    btn.disabled = loading;
}

elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError('login');
    setLoading(elements.loginForm, true);
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const data = await login(email, password);
        
        // Store token
        localStorage.setItem('eigencore_token', data.access_token);
        
        // Login response includes user
        showSuccess(data.user, 'Welcome back!');
        
    } catch (err) {
        showError('login', err.message);
    } finally {
        setLoading(elements.loginForm, false);
    }
});

elements.registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError('register');
    setLoading(elements.registerForm, true);
    
    const email = document.getElementById('register-email').value;
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    
    try {
        const registerData = await register(email, username, password);
        
        // Register returns {access_token, user} - store token
        localStorage.setItem('eigencore_token', registerData.access_token);
        
        showSuccess(registerData.user, 'Account created!');
        
    } catch (err) {
        showError('register', err.message);
    } finally {
        setLoading(elements.registerForm, false);
    }
});

// ==========================================================================
// OAuth
// ==========================================================================

elements.oauthButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const provider = btn.dataset.provider;
        
        // Redirect to OAuth endpoint
        // The API will redirect to the provider's auth page
        window.location.href = CONFIG.apiUrl + `/api/v1/auth/${provider}`;
    });
});

// Handle OAuth callback
function handleOAuthCallback() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const error = params.get('error');
    
    if (error) {
        // Switch to login tab and show error
        switchTab('login');
        showError('login', decodeURIComponent(error));
        // Clean URL
        window.history.replaceState({}, '', window.location.pathname);
        return;
    }
    
    if (token) {
        localStorage.setItem('eigencore_token', token);
        // Clean URL
        window.history.replaceState({}, '', window.location.pathname);
        
        // Get user info and show success
        getCurrentUser()
            .then(user => showSuccess(user, 'Connected!'))
            .catch(err => {
                showError('login', 'Failed to get user info');
                localStorage.removeItem('eigencore_token');
            });
    }
}

// ==========================================================================
// Success Modal
// ==========================================================================

function showSuccess(user, message) {
    elements.successMessage.textContent = message;
    
    const verificationNote = user.is_verified 
        ? '' 
        : '<p style="color: var(--warning); margin-top: var(--space-md); font-size: 0.875rem;">📧 Please check your email to verify your account.</p>';
    
    elements.userInfo.innerHTML = `
        <p><strong>Display Name:</strong> <span>${escapeHtml(user.display_name)}</span></p>
        <p><strong>Email:</strong> <span>${escapeHtml(user.email || 'N/A')}</span></p>
        <p><strong>ID:</strong> <span style="font-family: var(--font-mono); font-size: 0.75rem;">${user.id}</span></p>
        ${verificationNote}
    `;
    elements.modal.classList.add('visible');
}

function hideModal() {
    elements.modal.classList.remove('visible');
}

elements.modalClose.addEventListener('click', hideModal);

elements.modal.addEventListener('click', (e) => {
    if (e.target === elements.modal) {
        hideModal();
    }
});

// Escape key to close modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && elements.modal.classList.contains('visible')) {
        hideModal();
    }
});

// ==========================================================================
// Utilities
// ==========================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================================================
// Initialization
// ==========================================================================

function init() {
    // Check for OAuth callback
    handleOAuthCallback();
    
    // Check if already logged in
    const token = localStorage.getItem('eigencore_token');
    if (token) {
        getCurrentUser()
            .then(user => showSuccess(user, 'Already signed in'))
            .catch(() => {
                // Token invalid, remove it
                localStorage.removeItem('eigencore_token');
            });
    }
}

// Run on page load
init();
