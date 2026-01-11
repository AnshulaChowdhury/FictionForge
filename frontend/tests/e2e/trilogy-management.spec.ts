/**
 * E2E Tests: Trilogy Management
 *
 * Tests Epic 1: Create, Read, Update, Delete trilogies
 * Tests Primary Trilogy feature
 */

import { test, expect } from '@playwright/test'
import { TEST_USERS, login, createTrilogy, deleteTrilogy, setPrimaryTrilogy, cleanupTestData } from '../utils/test-helpers'
import { testTrilogies, generateUniqueTestData } from '../fixtures/test-data'

test.describe('Trilogy Management - Epic 1', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
  })

  test.afterEach(async ({ page }) => {
    // Clean up test data
    await cleanupTestData(page)
  })

  test('should display empty state when no trilogies exist', async ({ page }) => {
    await page.goto('/dashboard')

    // Should show empty state
    await expect(page.locator('text=/No trilogies/i')).toBeVisible()
    await expect(page.locator('button:has-text("Create"), button:has-text("New Trilogy")')).toBeVisible()
  })

  test('should create a new trilogy with all fields', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness

    // Create trilogy
    await createTrilogy(page, data)

    // Should show trilogy in list
    await expect(page.locator(`text=${data.title}`)).toBeVisible()
    await expect(page.locator(`text=${data.author}`)).toBeVisible()
    await expect(page.locator(`text=${data.description}`)).toBeVisible()

    // Should show success toast
    await expect(page.locator('[role="status"]:has-text("created"), [role="alert"]:has-text("created")')).toBeVisible()
  })

  test('should create trilogy with minimum required fields', async ({ page }) => {
    await page.goto('/dashboard')

    const data = generateUniqueTestData().trilogy

    // Create trilogy with only title and author
    await createTrilogy(page, {
      title: data.title,
      author: data.author
    })

    // Should show trilogy in list
    await expect(page.locator(`text=${data.title}`)).toBeVisible()
  })

  test('should view trilogy details', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness
    await createTrilogy(page, data)

    // Click on trilogy to view details
    await page.click(`text=${data.title}`)

    // Should navigate to trilogy detail page
    await expect(page).toHaveURL(/\/trilogy\/[a-f0-9-]+$/)

    // Should show trilogy details
    await expect(page.locator(`h1:has-text("${data.title}")`)).toBeVisible()
    await expect(page.locator(`text=${data.author}`)).toBeVisible()

    // Should show 3 books
    await expect(page.locator('text=Book 1')).toBeVisible()
    await expect(page.locator('text=Book 2')).toBeVisible()
    await expect(page.locator('text=Book 3')).toBeVisible()
  })

  test('should update trilogy narrative overview', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness
    await createTrilogy(page, data)

    // Navigate to trilogy detail
    await page.click(`text=${data.title}`)

    // Click edit button for narrative overview
    await page.click('button:has-text("Edit"):near(:text("Narrative Overview"))')

    // Update narrative overview
    const newOverview = 'Updated narrative overview for testing purposes.'
    await page.fill('textarea[name="narrative_overview"], textarea[id="edit-description"]', newOverview)
    await page.click('button:has-text("Save")')

    // Should show updated content
    await expect(page.locator(`text=${newOverview}`)).toBeVisible()
  })

  test('should update book titles', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness
    await createTrilogy(page, data)

    // Navigate to trilogy detail
    await page.click(`text=${data.title}`)

    // Edit Book 1 title
    await page.hover('text=Book 1')
    await page.click('button:has([class*="pencil"]):near(:text("Book 1"))')

    const newTitle = 'Awakening: The Beginning'
    await page.fill('input[value="Book 1"]', newTitle)
    await page.press('input[value="' + newTitle + '"]', 'Enter')

    // Should show updated title
    await expect(page.locator(`text=${newTitle}`)).toBeVisible()
  })

  test('should delete a trilogy', async ({ page }) => {
    await page.goto('/dashboard')

    const data = generateUniqueTestData().trilogy
    await createTrilogy(page, data)

    // Delete trilogy
    await deleteTrilogy(page, data.title)

    // Should not show trilogy in list
    await expect(page.locator(`text=${data.title}`)).not.toBeVisible()

    // Should show empty state if this was the only trilogy
    const trilogyCards = await page.locator('[data-testid="trilogy-card"], .trilogy-card').count()
    if (trilogyCards === 0) {
      await expect(page.locator('text=/No trilogies/i')).toBeVisible()
    }
  })

  test('should list all user trilogies sorted by creation date', async ({ page }) => {
    await page.goto('/dashboard')

    // Create multiple trilogies
    const trilogy1 = generateUniqueTestData().trilogy
    await createTrilogy(page, trilogy1)
    await page.waitForTimeout(1000) // Ensure different timestamps

    const trilogy2 = generateUniqueTestData().trilogy
    await createTrilogy(page, trilogy2)

    // Should show both trilogies
    await expect(page.locator(`text=${trilogy1.title}`)).toBeVisible()
    await expect(page.locator(`text=${trilogy2.title}`)).toBeVisible()

    // Newer trilogy should appear first (if sorted by newest)
    const cards = page.locator('[data-testid="trilogy-card"], .card, [class*="trilogy"]')
    const firstCard = cards.first()
    await expect(firstCard.locator(`text=${trilogy2.title}`)).toBeVisible()
  })
})

test.describe('Primary Trilogy Feature', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
  })

  test.afterEach(async ({ page }) => {
    await cleanupTestData(page)
  })

  test('should set trilogy as primary', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness
    await createTrilogy(page, data)

    // Set as primary
    await setPrimaryTrilogy(page, data.title)

    // Should show primary indicator
    const toggle = page.locator('label:has-text("Primary")').locator('..').locator('[role="switch"]')
    await expect(toggle).toHaveAttribute('data-state', 'checked')
  })

  test('should show primary trilogy in dashboard hero section', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await setPrimaryTrilogy(page, data.title)

    // Navigate back to dashboard
    await page.goto('/dashboard')

    // Should show primary trilogy in hero section
    await expect(page.locator('[class*="hero"], [class*="banner"]').first()).toContainText(data.title)
    await expect(page.locator('text=Active Project, text=Primary')).toBeVisible()
  })

  test('should only allow one primary trilogy', async ({ page }) => {
    await page.goto('/dashboard')

    // Create two trilogies
    const trilogy1 = generateUniqueTestData().trilogy
    await createTrilogy(page, trilogy1)

    const trilogy2 = generateUniqueTestData().trilogy
    await createTrilogy(page, trilogy2)

    // Set first as primary
    await setPrimaryTrilogy(page, trilogy1.title)

    // Navigate back to dashboard
    await page.goto('/dashboard')

    // Try to set second as primary
    await page.click(`text=${trilogy2.title}`)

    // Primary toggle should be disabled (greyed out)
    const toggle = page.locator('label:has-text("Primary")').locator('..').locator('[role="switch"]')
    await expect(toggle).toBeDisabled()
  })

  test('should show trilogy progress in hero section', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await setPrimaryTrilogy(page, data.title)

    await page.goto('/dashboard')

    // Should show progress metrics
    await expect(page.locator('text=/Total Words/i')).toBeVisible()
    await expect(page.locator('text=/Estimated Pages/i')).toBeVisible()
    await expect(page.locator('text=/Chapters/i')).toBeVisible()
  })
})

test.describe('Dashboard Features', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
  })

  test.afterEach(async ({ page }) => {
    await cleanupTestData(page)
  })

  test('should display user welcome message', async ({ page }) => {
    await page.goto('/dashboard')

    // Should show welcome message with user name or email
    await expect(page.locator('text=Welcome back')).toBeVisible()
  })

  test('should navigate to trilogy creation', async ({ page }) => {
    await page.goto('/dashboard')

    await page.click('button:has-text("Create New Trilogy"), button:has-text("Create")')

    // Should open create dialog
    await expect(page.locator('[role="dialog"]')).toBeVisible()
    await expect(page.locator('text=/Create.*Trilogy/i')).toBeVisible()
  })

  test('should provide quick actions from hero section', async ({ page }) => {
    await page.goto('/dashboard')

    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await setPrimaryTrilogy(page, data.title)

    await page.goto('/dashboard')

    // Should show quick action buttons
    await expect(page.locator('button:has-text("Characters")')).toBeVisible()
    await expect(page.locator('button:has-text("World Rules")')).toBeVisible()
  })
})
