/**
 * Eigencore Dashboard - Shared functionality
 * 
 * This module handles:
 * - User authentication state (token in localStorage)
 * - Loading and displaying user info
 * - Sidebar navigation and user menu
 * - Logout functionality
 * - Welcome banner for new users
 * 
 * Included on dashboard.html, settings.html, and other authenticated pages.
 * Automatically redirects to login if no valid token is found.
 * 
 * Global: window.eigencore.user - Current user object after loadUser()
 * Global: window.eigencore.token - JWT token from localStorage
 */

// Configuration
const CONFIG = {
    apiUrl: window.EIGENCORE_API_URL || '',
};

// Global state
window.eigencore = {
    user: null,
    token: localStorage.getItem('eigencore_token'),
};

// ==========================================================================
// API Helpers
// ==========================================================================

async function apiCall(endpoint, options = {}) {
    const url = CONFIG.apiUrl + endpoint;
    
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    if (window.eigencore.token) {
        defaults.headers['Authorization'] = `Bearer ${window.eigencore.token}`;
    }
    
    const response = await fetch(url, { ...defaults, ...options });
    
    if (response.status === 401) {
        // Token invalid, redirect to login
        logout();
        return;
    }
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.detail || 'An error occurred');
    }
    
    return data;
}

// ==========================================================================
// Authentication
// ==========================================================================

async function loadUser() {
    if (!window.eigencore.token) {
        redirectToLogin();
        return;
    }
    
    try {
        const user = await apiCall('/api/v1/auth/me');
        window.eigencore.user = user;
        updateUserUI(user);
        return user;
    } catch (err) {
        console.error('Failed to load user:', err);
        logout();
    }
}

function logout() {
    localStorage.removeItem('eigencore_token');
    localStorage.removeItem('eigencore_welcome_dismissed');
    window.eigencore.token = null;
    window.eigencore.user = null;
    redirectToLogin();
}

function redirectToLogin() {
    window.location.href = '/';
}

// ==========================================================================
// UI Updates
// ==========================================================================

function updateUserUI(user) {
    // Update sidebar user info
    const userNameEl = document.getElementById('user-name');
    const userEmailEl = document.getElementById('user-email');
    const userAvatarEl = document.getElementById('user-avatar');
    
    if (userNameEl) userNameEl.textContent = user.display_name;
    if (userEmailEl) userEmailEl.textContent = user.email || 'No email';
    
    if (userAvatarEl) {
        if (user.avatar_url) {
            userAvatarEl.innerHTML = `<img src="${escapeHtml(user.avatar_url)}" alt="">`;
        } else {
            userAvatarEl.textContent = getInitial(user.display_name);
        }
    }
    
    // Update welcome banner if present
    const welcomeNameEl = document.getElementById('welcome-name');
    if (welcomeNameEl) {
        welcomeNameEl.textContent = user.display_name;
    }
    
    // Show welcome banner for new users (created in last hour)
    const welcomeBanner = document.getElementById('welcome-banner');
    if (welcomeBanner) {
        const createdAt = new Date(user.created_at);
        const hourAgo = new Date(Date.now() - 60 * 60 * 1000);
        const dismissed = localStorage.getItem('eigencore_welcome_dismissed');
        
        if (createdAt > hourAgo && !dismissed) {
            welcomeBanner.style.display = 'block';
        }
    }
}

function getInitial(name) {
    return name ? name.charAt(0).toUpperCase() : '?';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================================================
// Event Handlers
// ==========================================================================

function initSidebar() {
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('Sign out of Eigencore?')) {
                logout();
            }
        });
    }
    
    // Dismiss welcome banner
    const dismissWelcome = document.getElementById('dismiss-welcome');
    if (dismissWelcome) {
        dismissWelcome.addEventListener('click', () => {
            const banner = document.getElementById('welcome-banner');
            if (banner) {
                banner.style.display = 'none';
                localStorage.setItem('eigencore_welcome_dismissed', 'true');
            }
        });
    }
}

// ==========================================================================
// Initialization
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    loadUser();
});
