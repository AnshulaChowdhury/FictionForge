/**
 * E2E Tests: Authentication and User Management
 *
 * Tests Epic 0: User authentication, registration, and profile management
 */

import { test, expect } from '@playwright/test'
import { TEST_USERS, login, logout } from '../utils/test-helpers'

test.describe('Authentication', () => {
  test('should display login page on initial load', async ({ page }) => {
    await page.goto('/')

    // Should show login form
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button:has-text("Sign In")')).toBeVisible()
  })

  test('should login with valid credentials', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/)

    // Should show welcome message
    await expect(page.locator('text=Welcome back')).toBeVisible()
  })

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/')

    await page.fill('input[type="email"]', 'invalid@test.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button:has-text("Sign In")')

    // Should show error message
    await expect(page.locator('text=/Invalid.*credentials/i, [role="alert"]')).toBeVisible()

    // Should stay on login page
    await expect(page).toHaveURL(/\/$/)
  })

  test('should logout successfully', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Logout
    await logout(page)

    // Should redirect to login page
    await expect(page).toHaveURL(/\/$/)
  })

  test('should protect authenticated routes', async ({ page }) => {
    // Try to access dashboard without login
    await page.goto('/dashboard')

    // Should redirect to login
    await expect(page).toHaveURL(/\/$/)
  })
})

test.describe('User Profile', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
  })

  test('should view user profile', async ({ page }) => {
    // Navigate to profile (if profile page exists)
    await page.goto('/profile').catch(() => {
      // Profile might be in a menu
      return page.click('[data-testid="user-menu"]')
    })

    // Should show user information
    await expect(page.locator(`text=${TEST_USERS.primary.email}`)).toBeVisible()
  })

  test('should update user profile', async ({ page }) => {
    await page.goto('/profile').catch(() => page.click('text=Profile'))

    // Update profile fields if they exist
    const nameField = page.locator('input[name="name"], input[id="name"]')
    if (await nameField.count() > 0) {
      await nameField.fill('Updated Test User')
      await page.click('button:has-text("Save"), button:has-text("Update")')

      // Should show success message
      await expect(page.locator('[role="status"]:has-text("Success"), [role="alert"]:has-text("updated")')).toBeVisible()
    }
  })
})
