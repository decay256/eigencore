// @ts-check
const { test, expect } = require('@playwright/test');

// Shared test user - created fresh each run
const testEmail = `dashboard-${Date.now()}@test.com`;
const testPassword = 'TestPass123!';
let authToken = null;

test.describe('Dashboard', () => {
  
  test.beforeAll(async ({ request }) => {
    // Create a test user via API
    const response = await request.post('/api/v1/auth/register', {
      data: {
        email: testEmail,
        password: testPassword,
        display_name: 'Dashboard Tester'
      }
    });
    const data = await response.json();
    authToken = data.access_token;
  });

  test('redirects to login when not authenticated', async ({ page }) => {
    // Clear any stored token
    await page.goto('/');
    await page.evaluate(() => localStorage.removeItem('eigencore_token'));
    
    // Try to access dashboard
    await page.goto('/dashboard.html');
    
    // Should redirect to login (index)
    await page.waitForURL('/', { timeout: 5000 });
  });

  test('shows dashboard when authenticated', async ({ page }) => {
    await page.goto('/');
    
    // Set token in localStorage
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
    }, authToken);
    
    await page.goto('/dashboard.html');
    
    // Should show dashboard elements
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.page-header h1')).toContainText('Home');
    await expect(page.locator('.nav-item.active')).toContainText('Home');
  });

  test('displays user info in sidebar', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
    }, authToken);
    
    await page.goto('/dashboard.html');
    
    // Wait for user info to load
    await expect(page.locator('#user-name')).toContainText('Dashboard Tester', { timeout: 5000 });
    await expect(page.locator('#user-email')).toContainText(testEmail);
  });

  test('sidebar navigation works', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
    }, authToken);
    
    await page.goto('/dashboard.html');
    
    // Click settings link
    await page.click('a[href="settings.html"]');
    
    // Should navigate to settings
    await expect(page).toHaveURL(/settings\.html/);
    await expect(page.locator('.page-header h1')).toContainText('Settings');
  });

  test('logout button works', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
    }, authToken);
    
    await page.goto('/dashboard.html');
    
    // Accept the confirm dialog
    page.on('dialog', dialog => dialog.accept());
    
    // Click logout
    await page.click('#logout-btn');
    
    // Should redirect to login
    await page.waitForURL('/', { timeout: 5000 });
    
    // Token should be removed
    const token = await page.evaluate(() => localStorage.getItem('eigencore_token'));
    expect(token).toBeNull();
  });

  test('welcome banner shows for new users', async ({ page }) => {
    await page.goto('/');
    
    // Clear welcome dismissed flag
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
      localStorage.removeItem('eigencore_welcome_dismissed');
    }, authToken);
    
    await page.goto('/dashboard.html');
    
    // Welcome banner should be visible (user was just created)
    await expect(page.locator('#welcome-banner')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#welcome-name')).toContainText('Dashboard Tester');
  });

  test('welcome banner can be dismissed', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((token) => {
      localStorage.setItem('eigencore_token', token);
      localStorage.removeItem('eigencore_welcome_dismissed');
    }, authToken);
    
    await page.goto('/dashboard.html');
    
    // Dismiss welcome banner
    await page.click('#dismiss-welcome');
    
    // Should be hidden
    await expect(page.locator('#welcome-banner')).not.toBeVisible();
    
    // Reload - should stay hidden
    await page.reload();
    await expect(page.locator('#welcome-banner')).not.toBeVisible();
  });
});
