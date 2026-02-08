// @ts-check
const { test, expect } = require('@playwright/test');

// Shared test user
const testEmail = `settings-${Date.now()}@test.com`;
const testPassword = 'TestPass123!';
let authToken = null;

test.describe('Settings', () => {
  
  test.beforeAll(async ({ request }) => {
    // Create a test user via API
    const response = await request.post('/api/v1/auth/register', {
      data: {
        email: testEmail,
        password: testPassword,
        display_name: 'Settings Tester'
      }
    });
    const data = await response.json();
    authToken = data.access_token;
  });

  test.beforeEach(async ({ page }) => {
    // Set auth token before each test
    await page.goto('/');
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
    }, authToken);
  });

  test('loads settings page with profile tab active', async ({ page }) => {
    await page.goto('/settings.html');
    
    await expect(page.locator('.page-header h1')).toContainText('Settings');
    await expect(page.locator('.settings-tab.active')).toContainText('Profile');
    await expect(page.locator('#panel-profile')).toBeVisible();
  });

  test('profile form shows current user data', async ({ page }) => {
    await page.goto('/settings.html');
    
    // Wait for form to populate
    await expect(page.locator('#display-name')).toHaveValue('Settings Tester', { timeout: 5000 });
    await expect(page.locator('#email')).toHaveValue(testEmail);
    await expect(page.locator('#user-id')).not.toBeEmpty();
  });

  test('can update display name', async ({ page }) => {
    await page.goto('/settings.html');
    
    // Wait for form to load
    await expect(page.locator('#display-name')).toHaveValue('Settings Tester', { timeout: 5000 });
    
    // Change display name
    await page.fill('#display-name', 'Updated Name');
    await page.click('#profile-form button[type="submit"]');
    
    // Should show success message
    await expect(page.locator('#profile-message')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#profile-message')).toContainText(/success/i);
    
    // Sidebar should update
    await expect(page.locator('#user-name')).toContainText('Updated Name');
  });

  test('tab switching works', async ({ page }) => {
    await page.goto('/settings.html');
    
    // Click Security tab
    await page.click('.settings-tab[data-tab="security"]');
    await expect(page.locator('#panel-security')).toBeVisible();
    await expect(page.locator('#panel-profile')).not.toBeVisible();
    
    // Click Connections tab
    await page.click('.settings-tab[data-tab="connections"]');
    await expect(page.locator('#panel-connections')).toBeVisible();
    
    // Click Danger Zone tab
    await page.click('.settings-tab[data-tab="danger"]');
    await expect(page.locator('#panel-danger')).toBeVisible();
    await expect(page.locator('.settings-card.danger')).toBeVisible();
  });

  test('hash navigation works', async ({ page }) => {
    await page.goto('/settings.html#security');
    
    // Security tab should be active
    await expect(page.locator('.settings-tab[data-tab="security"]')).toHaveClass(/active/);
    await expect(page.locator('#panel-security')).toBeVisible();
  });

  test('password change validation', async ({ page }) => {
    await page.goto('/settings.html#security');
    
    // Try to submit with mismatched passwords
    await page.fill('#current-password', testPassword);
    await page.fill('#new-password', 'newpassword123');
    await page.fill('#confirm-password', 'differentpassword');
    await page.click('#password-form button[type="submit"]');
    
    // Should show error
    await expect(page.locator('#password-message')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#password-message')).toContainText(/match/i);
  });

  test('connections tab shows OAuth providers', async ({ page }) => {
    await page.goto('/settings.html#connections');
    
    await expect(page.locator('#connection-discord')).toBeVisible();
    await expect(page.locator('#connection-google')).toBeVisible();
    await expect(page.locator('#connection-steam')).toBeVisible();
  });

  test('delete account modal requires confirmation', async ({ page }) => {
    await page.goto('/settings.html#danger');
    
    // Click delete button
    await page.click('#delete-account-btn');
    
    // Modal should appear
    await expect(page.locator('#delete-modal')).toBeVisible();
    
    // Confirm button should be disabled
    await expect(page.locator('#confirm-delete-btn')).toBeDisabled();
    
    // Type wrong confirmation
    await page.fill('#confirm-delete', 'delete');
    await expect(page.locator('#confirm-delete-btn')).toBeDisabled();
    
    // Type correct confirmation
    await page.fill('#confirm-delete', 'DELETE');
    await expect(page.locator('#confirm-delete-btn')).toBeEnabled();
    
    // Cancel
    await page.click('#cancel-delete');
    await expect(page.locator('#delete-modal')).not.toBeVisible();
  });
});

test.describe('Account Deletion', () => {
  test('can delete account', async ({ page, request }) => {
    // Create a throwaway user for deletion test
    const deleteEmail = `delete-${Date.now()}@test.com`;
    const response = await request.post('/api/v1/auth/register', {
      data: {
        email: deleteEmail,
        password: 'TestPass123!',
        display_name: 'Delete Me'
      }
    });
    const { access_token } = await response.json();
    
    await page.goto('/');
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
    }, access_token);
    
    await page.goto('/settings.html#danger');
    
    // Delete account
    await page.click('#delete-account-btn');
    await page.fill('#confirm-delete', 'DELETE');
    await page.click('#confirm-delete-btn');
    
    // Should redirect to login with message
    await page.waitForURL('/?deleted=true', { timeout: 10000 });
    await expect(page.locator('#login-error')).toContainText(/deleted/i);
  });
});
