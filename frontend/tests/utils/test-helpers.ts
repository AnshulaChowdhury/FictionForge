/**
 * E2E Test Helper Functions
 *
 * Utility functions for Playwright E2E tests
 * Provides reusable test actions and assertions
 */

import { Page, expect } from '@playwright/test'

/**
 * Test user credentials for authentication tests
 */
export const TEST_USERS = {
  primary: {
    email: 'test-user@novelapp.test',
    password: 'TestPassword123!',
    name: 'Test User'
  },
  secondary: {
    email: 'test-user-2@novelapp.test',
    password: 'TestPassword456!',
    name: 'Test User 2'
  }
}

/**
 * Login as a test user
 */
export async function login(page: Page, email: string, password: string) {
  await page.goto('/')

  // Fill in login credentials
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)

  // Click sign in button
  await page.click('button:has-text("Sign In")')

  // Wait for navigation to dashboard
  await page.waitForURL('**/dashboard', { timeout: 10000 })
}

/**
 * Logout the current user
 */
export async function logout(page: Page) {
  // Click user menu or logout button
  await page.click('[data-testid="user-menu"]', { timeout: 5000 }).catch(() => {
    // If testid not found, try text
    return page.click('text=Logout')
  })

  // Wait for redirect to login
  await page.waitForURL('**/', { timeout: 5000 })
}

/**
 * Create a new trilogy
 */
export async function createTrilogy(
  page: Page,
  data: {
    title: string
    author: string
    description?: string
    narrative_overview?: string
  }
) {
  // Click Create New Trilogy button
  await page.click('button:has-text("Create New Trilogy")')

  // Wait for dialog
  await page.waitForSelector('[role="dialog"]')

  // Fill in form
  await page.fill('input[name="title"], input[id="title"]', data.title)
  await page.fill('input[name="author"], input[id="author"]', data.author)

  if (data.description) {
    await page.fill('textarea[name="description"], textarea[id="description"]', data.description)
  }

  if (data.narrative_overview) {
    await page.fill('textarea[name="narrative_overview"], textarea[id="narrative_overview"]', data.narrative_overview)
  }

  // Submit form
  await page.click('button:has-text("Create")')

  // Wait for success - dialog should close
  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 })

  // Return to verify trilogy was created
  return page.waitForSelector(`text=${data.title}`, { timeout: 5000 })
}

/**
 * Delete a trilogy
 */
export async function deleteTrilogy(page: Page, trilogyTitle: string) {
  // Find the trilogy card and click delete button
  const card = page.locator(`text=${trilogyTitle}`).locator('..').locator('..')
  await card.locator('[title="Delete"], button:has-text("Delete")').first().click()

  // Confirm deletion
  await page.click('button:has-text("Delete Trilogy"), button:has-text("Delete")')

  // Wait for trilogy to disappear
  await page.waitForSelector(`text=${trilogyTitle}`, { state: 'hidden', timeout: 5000 })
}

/**
 * Set a trilogy as primary
 */
export async function setPrimaryTrilogy(page: Page, trilogyTitle: string) {
  // Navigate to trilogy detail page
  await page.click(`text=${trilogyTitle}`)
  await page.waitForLoadState('networkidle')

  // Find and click the Primary toggle
  const toggle = page.locator('label:has-text("Primary")').locator('..').locator('[role="switch"]')
  const isChecked = await toggle.getAttribute('data-state')

  if (isChecked !== 'checked') {
    await toggle.click()
    // Wait for the toggle to update
    await page.waitForTimeout(500)
  }
}

/**
 * Create a character
 */
export async function createCharacter(
  page: Page,
  data: {
    name: string
    description?: string
    personality_traits?: string
    speech_patterns?: string
  }
) {
  // Click Create Character button
  await page.click('button:has-text("Add Character"), button:has-text("Create Character")')

  // Wait for dialog
  await page.waitForSelector('[role="dialog"]')

  // Fill in form
  await page.fill('input[name="name"], input[id="name"]', data.name)

  if (data.description) {
    await page.fill('textarea[name="description"], textarea[id="description"]', data.description)
  }

  if (data.personality_traits) {
    await page.fill('textarea[name="personality_traits"], textarea[id="personality_traits"]', data.personality_traits)
  }

  if (data.speech_patterns) {
    await page.fill('textarea[name="speech_patterns"], textarea[id="speech_patterns"]', data.speech_patterns)
  }

  // Submit
  await page.click('button:has-text("Create"), button:has-text("Save")')

  // Wait for dialog to close
  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 })
}

/**
 * Create a world rule
 */
export async function createWorldRule(
  page: Page,
  data: {
    title: string
    description: string
    category?: string
  }
) {
  // Click Create World Rule button
  await page.click('button:has-text("Add Rule"), button:has-text("Create Rule")')

  // Wait for dialog
  await page.waitForSelector('[role="dialog"]')

  // Fill in form
  await page.fill('input[name="title"], input[id="title"]', data.title)
  await page.fill('textarea[name="description"], textarea[id="description"]', data.description)

  if (data.category) {
    // Select category if dropdown is present
    await page.click('[role="combobox"]')
    await page.click(`[role="option"]:has-text("${data.category}")`)
  }

  // Submit
  await page.click('button:has-text("Create"), button:has-text("Save")')

  // Wait for dialog to close
  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 })
}

/**
 * Create a chapter
 */
export async function createChapter(
  page: Page,
  data: {
    title: string
    character: string
    plot_notes?: string
    target_word_count?: number
  }
) {
  // Click Add Chapter button
  await page.click('button:has-text("Add Chapter")')

  // Wait for dialog
  await page.waitForSelector('[role="dialog"]')

  // Fill in form
  await page.fill('input[name="title"], input[id="title"]', data.title)

  // Select character from dropdown
  await page.click('[role="combobox"]')
  await page.click(`[role="option"]:has-text("${data.character}")`)

  if (data.plot_notes) {
    await page.fill('textarea[id="description"], textarea[name="chapter_plot"]', data.plot_notes)
  }

  if (data.target_word_count) {
    await page.fill('input[id="target_word_count"], input[name="target_word_count"]', data.target_word_count.toString())
  }

  // Submit
  await page.click('button:has-text("Create Chapter")')

  // Wait for dialog to close
  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 })
}

/**
 * Wait for toast notification
 */
export async function waitForToast(page: Page, message?: string, timeout = 5000) {
  if (message) {
    await page.waitForSelector(`[role="status"]:has-text("${message}"), [role="alert"]:has-text("${message}")`, { timeout })
  } else {
    await page.waitForSelector('[role="status"], [role="alert"]', { timeout })
  }
}

/**
 * Navigate to a specific trilogy
 */
export async function navigateToTrilogy(page: Page, trilogyTitle: string) {
  await page.goto('/dashboard')
  await page.click(`text=${trilogyTitle}`)
  await page.waitForLoadState('networkidle')
}

/**
 * Navigate to characters page for a trilogy
 */
export async function navigateToCharacters(page: Page, trilogyTitle: string) {
  await navigateToTrilogy(page, trilogyTitle)
  await page.click('button:has-text("Characters")')
  await page.waitForURL('**/characters')
}

/**
 * Navigate to world rules page for a trilogy
 */
export async function navigateToWorldRules(page: Page, trilogyTitle: string) {
  await navigateToTrilogy(page, trilogyTitle)
  await page.click('button:has-text("World Rules")')
  await page.waitForURL('**/world-rules')
}

/**
 * Clean up test data - delete all trilogies for test user
 */
export async function cleanupTestData(page: Page) {
  await page.goto('/dashboard')

  // Find and delete all trilogies
  const deleteButtons = await page.locator('button:has-text("Delete"), [title="Delete"]').all()

  for (const button of deleteButtons) {
    try {
      await button.click()
      await page.click('button:has-text("Delete Trilogy"), button:has-text("Delete")')
      await page.waitForTimeout(500)
    } catch (e) {
      // Ignore errors - trilogy might already be deleted
    }
  }
}
