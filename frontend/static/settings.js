/**
 * Eigencore Settings - Settings page functionality
 */

// Wait for dashboard.js to load user
let settingsReady = false;

// ==========================================================================
// Settings Tabs
// ==========================================================================

function initSettingsTabs() {
    const tabs = document.querySelectorAll('.settings-tab');
    const panels = document.querySelectorAll('.settings-panel');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;
            
            // Update tabs
            tabs.forEach(t => t.classList.toggle('active', t === tab));
            
            // Update panels
            panels.forEach(p => {
                p.classList.toggle('active', p.id === `panel-${targetTab}`);
            });
            
            // Update URL hash
            history.replaceState(null, '', `#${targetTab}`);
        });
    });
    
    // Handle initial hash
    const hash = window.location.hash.slice(1);
    if (hash) {
        const tab = document.querySelector(`.settings-tab[data-tab="${hash}"]`);
        if (tab) tab.click();
    }
}

// ==========================================================================
// Profile Form
// ==========================================================================

function initProfileForm() {
    const form = document.getElementById('profile-form');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = form.querySelector('.btn-primary');
        btn.classList.add('loading');
        btn.disabled = true;
        
        try {
            const displayName = document.getElementById('display-name').value;
            const avatarUrl = document.getElementById('avatar-image').src || null;
            
            const body = { display_name: displayName };
            
            // Only send avatar_url if it changed
            const currentAvatar = window.eigencore.user?.avatar_url || '';
            if (avatarUrl !== currentAvatar) {
                body.avatar_url = avatarUrl || '';
            }
            
            const user = await apiCall('/api/v1/auth/me', {
                method: 'PATCH',
                body: JSON.stringify(body),
            });
            
            window.eigencore.user = user;
            updateUserUI(user);
            showMessage('profile-message', 'Profile updated successfully', 'success');
            
        } catch (err) {
            showMessage('profile-message', err.message, 'error');
        } finally {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    });
    
    // Avatar upload handling
    const avatarInput = document.getElementById('avatar-input');
    const avatarPreview = document.getElementById('avatar-preview');
    const avatarImage = document.getElementById('avatar-image');
    const avatarInitial = document.getElementById('avatar-initial');
    const removeAvatar = document.getElementById('remove-avatar');
    
    if (avatarInput) {
        avatarInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            // Validate size (2MB max)
            if (file.size > 2 * 1024 * 1024) {
                showMessage('profile-message', 'Avatar must be under 2MB', 'error');
                return;
            }
            
            // Preview
            const reader = new FileReader();
            reader.onload = (e) => {
                avatarImage.src = e.target.result;
                avatarImage.style.display = 'block';
                avatarInitial.style.display = 'none';
            };
            reader.readAsDataURL(file);
        });
    }
    
    if (removeAvatar) {
        removeAvatar.addEventListener('click', () => {
            avatarImage.src = '';
            avatarImage.style.display = 'none';
            avatarInitial.style.display = 'block';
            if (avatarInput) avatarInput.value = '';
        });
    }
}

function populateProfileForm(user) {
    const displayNameInput = document.getElementById('display-name');
    const emailInput = document.getElementById('email');
    const emailStatus = document.getElementById('email-status');
    const userIdField = document.getElementById('user-id');
    const createdAtField = document.getElementById('created-at');
    const avatarImage = document.getElementById('avatar-image');
    const avatarInitial = document.getElementById('avatar-initial');
    
    if (displayNameInput) displayNameInput.value = user.display_name;
    if (emailInput) emailInput.value = user.email || 'N/A (OAuth account)';
    
    if (emailStatus) {
        if (!user.email) {
            emailStatus.textContent = 'OAuth account - no email required';
        } else if (user.is_verified) {
            emailStatus.innerHTML = '<span style="color: var(--success);">✓ Verified</span>';
        } else {
            emailStatus.innerHTML = '<span style="color: var(--warning);">⚠ Not verified - check your email</span>';
        }
    }
    
    if (userIdField) userIdField.textContent = user.id;
    
    if (createdAtField) {
        const date = new Date(user.created_at);
        createdAtField.textContent = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    }
    
    if (user.avatar_url && avatarImage) {
        avatarImage.src = user.avatar_url;
        avatarImage.style.display = 'block';
        if (avatarInitial) avatarInitial.style.display = 'none';
    } else if (avatarInitial) {
        avatarInitial.textContent = getInitial(user.display_name);
    }
}

// ==========================================================================
// Password Form
// ==========================================================================

function initPasswordForm() {
    const form = document.getElementById('password-form');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const currentPassword = document.getElementById('current-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        
        // Validate passwords match
        if (newPassword !== confirmPassword) {
            showMessage('password-message', 'New passwords do not match', 'error');
            return;
        }
        
        const btn = form.querySelector('.btn-primary');
        btn.classList.add('loading');
        btn.disabled = true;
        
        try {
            await apiCall('/api/v1/auth/change-password', {
                method: 'POST',
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            });
            
            showMessage('password-message', 'Password changed successfully', 'success');
            form.reset();
            
        } catch (err) {
            showMessage('password-message', err.message, 'error');
        } finally {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    });
}

function updatePasswordFormVisibility(user) {
    const form = document.getElementById('password-form');
    const description = document.getElementById('password-description');
    
    if (!form) return;
    
    // OAuth-only accounts can't change password
    if (user.oauth_provider && !user.email) {
        form.style.display = 'none';
        if (description) {
            description.innerHTML = `
                <span style="color: var(--text-muted);">
                    You signed in with ${user.oauth_provider}. Password management is handled by your OAuth provider.
                </span>
            `;
        }
    }
}

// ==========================================================================
// Connections
// ==========================================================================

function initConnections() {
    const connectButtons = document.querySelectorAll('.connection-item button[data-provider]');
    
    connectButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const provider = btn.dataset.provider;
            // Redirect to OAuth flow
            window.location.href = CONFIG.apiUrl + `/api/v1/auth/${provider}`;
        });
    });
}

function updateConnectionsUI(user) {
    const discordStatus = document.getElementById('discord-status');
    const googleStatus = document.getElementById('google-status');
    const steamStatus = document.getElementById('steam-status');
    
    // For now, just show if OAuth provider matches
    // Later: support multiple linked accounts
    if (user.oauth_provider === 'discord' && discordStatus) {
        discordStatus.textContent = 'Connected';
        discordStatus.style.color = 'var(--success)';
        const btn = discordStatus.closest('.connection-item').querySelector('button');
        if (btn) {
            btn.textContent = 'Connected';
            btn.disabled = true;
        }
    }
    
    if (user.oauth_provider === 'google' && googleStatus) {
        googleStatus.textContent = 'Connected';
        googleStatus.style.color = 'var(--success)';
        const btn = googleStatus.closest('.connection-item').querySelector('button');
        if (btn) {
            btn.textContent = 'Connected';
            btn.disabled = true;
        }
    }
    
    if (user.oauth_provider === 'steam' && steamStatus) {
        steamStatus.textContent = 'Connected';
        steamStatus.style.color = 'var(--success)';
        const btn = steamStatus.closest('.connection-item').querySelector('button');
        if (btn) {
            btn.textContent = 'Connected';
            btn.disabled = true;
        }
    }
}

// ==========================================================================
// Account Deletion
// ==========================================================================

function initDeleteAccount() {
    const deleteBtn = document.getElementById('delete-account-btn');
    const modal = document.getElementById('delete-modal');
    const cancelBtn = document.getElementById('cancel-delete');
    const confirmBtn = document.getElementById('confirm-delete-btn');
    const confirmInput = document.getElementById('confirm-delete');
    
    if (!deleteBtn || !modal) return;
    
    deleteBtn.addEventListener('click', () => {
        modal.classList.add('visible');
        confirmInput.value = '';
        confirmBtn.disabled = true;
    });
    
    cancelBtn.addEventListener('click', () => {
        modal.classList.remove('visible');
    });
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('visible');
        }
    });
    
    confirmInput.addEventListener('input', () => {
        confirmBtn.disabled = confirmInput.value !== 'DELETE';
    });
    
    confirmBtn.addEventListener('click', async () => {
        if (confirmInput.value !== 'DELETE') return;
        
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Deleting...';
        
        try {
            await apiCall('/api/v1/auth/me', { method: 'DELETE' });
            
            // Clear local state and redirect
            localStorage.removeItem('eigencore_token');
            localStorage.removeItem('eigencore_welcome_dismissed');
            window.location.href = '/?deleted=true';
            
        } catch (err) {
            alert('Failed to delete account: ' + err.message);
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Delete Forever';
        }
    });
}

// ==========================================================================
// Utilities
// ==========================================================================

function showMessage(elementId, message, type) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    el.textContent = message;
    el.className = `form-message ${type}`;
    el.style.display = 'block';
    
    // Auto-hide success messages
    if (type === 'success') {
        setTimeout(() => {
            el.style.display = 'none';
        }, 5000);
    }
}

// ==========================================================================
// Initialization
// ==========================================================================

function initSettings() {
    if (settingsReady) return;
    settingsReady = true;
    
    initSettingsTabs();
    initProfileForm();
    initPasswordForm();
    initConnections();
    initDeleteAccount();
}

// Wait for user to load, then populate forms
const originalLoadUser = window.loadUser;
window.loadUser = async function() {
    const user = await originalLoadUser.call(this);
    if (user) {
        populateProfileForm(user);
        updatePasswordFormVisibility(user);
        updateConnectionsUI(user);
    }
    return user;
};

document.addEventListener('DOMContentLoaded', initSettings);
