// @ts-check
const { test, expect } = require('@playwright/test');

// Generate unique email for each test run
const testEmail = `e2e-${Date.now()}@test.com`;
const testUsername = `e2euser${Date.now()}`;
const testPassword = 'TestPass123!';

test.describe('Authentication', () => {
  
  test('should load the login page', async ({ page }) => {
    await page.goto('/');
    
    // Check page title
    await expect(page).toHaveTitle(/Eigencore/);
    
    // Check main elements exist
    await expect(page.locator('h1')).toContainText('Eigencore');
    await expect(page.locator('#login-form')).toBeVisible();
    await expect(page.locator('button[data-tab="register"]')).toBeVisible();
  });

  test('should switch to register tab', async ({ page }) => {
    await page.goto('/');
    
    // Click register tab
    await page.click('button[data-tab="register"]');
    
    // Check register form is visible
    await expect(page.locator('#register-form')).toBeVisible();
    await expect(page.locator('#login-form')).not.toBeVisible();
  });

  test('should register a new user', async ({ page }) => {
    await page.goto('/');
    
    // Switch to register tab
    await page.click('button[data-tab="register"]');
    
    // Fill in registration form
    await page.fill('#register-email', testEmail);
    await page.fill('#register-username', testUsername);
    await page.fill('#register-password', testPassword);
    
    // Submit form
    await page.click('#register-form button[type="submit"]');
    
    // Wait for success modal
    await expect(page.locator('#success-modal')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#success-message')).toContainText(/Account created|Welcome/);
    
    // Verify user info displayed
    await expect(page.locator('#user-info')).toContainText(testEmail);
  });

  test('should show error for duplicate email', async ({ page }) => {
    await page.goto('/');
    
    // Switch to register tab
    await page.click('button[data-tab="register"]');
    
    // Try to register with same email
    await page.fill('#register-email', testEmail);
    await page.fill('#register-username', 'duplicate');
    await page.fill('#register-password', testPassword);
    
    await page.click('#register-form button[type="submit"]');
    
    // Should show error
    await expect(page.locator('#register-error')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#register-error')).toContainText(/already registered/i);
  });

  test('should login with registered user', async ({ page }) => {
    await page.goto('/');
    
    // Fill login form
    await page.fill('#login-email', testEmail);
    await page.fill('#login-password', testPassword);
    
    // Submit
    await page.click('#login-form button[type="submit"]');
    
    // Wait for success modal
    await expect(page.locator('#success-modal')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#success-message')).toContainText(/Welcome back|signed in/i);
  });

  test('should show error for wrong password', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('#login-email', testEmail);
    await page.fill('#login-password', 'wrongpassword');
    
    await page.click('#login-form button[type="submit"]');
    
    // Should show error
    await expect(page.locator('#login-error')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#login-error')).toContainText(/Invalid|password/i);
  });

  test('OAuth buttons should exist', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.locator('.btn-discord')).toBeVisible();
    await expect(page.locator('.btn-google')).toBeVisible();
    await expect(page.locator('.btn-steam')).toBeVisible();
  });
});
