/**
 * E2E Tests: Character Management
 *
 * Tests Epic 2: Create, manage, and embed characters with RAG
 */

import { test, expect } from '@playwright/test'
import { TEST_USERS, login, createTrilogy, createCharacter, navigateToCharacters, cleanupTestData } from '../utils/test-helpers'
import { testTrilogies, testCharacters, generateUniqueTestData } from '../fixtures/test-data'

test.describe('Character Management - Epic 2', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create a trilogy for character tests
    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToCharacters(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should display empty state when no characters exist', async ({ page }) => {
    // Should show empty state
    await expect(page.locator('text=/No characters/i')).toBeVisible()
    await expect(page.locator('button:has-text("Create"), button:has-text("Add Character")')).toBeVisible()
  })

  test('should create a character with all fields', async ({ page }) => {
    const data = testCharacters.kira

    await createCharacter(page, data)

    // Should show character in list
    await expect(page.locator(`text=${data.name}`)).toBeVisible()
    await expect(page.locator(`text=${data.description}`)).toBeVisible()
  })

  test('should create character with minimum required fields', async ({ page }) => {
    const data = generateUniqueTestData().character

    await createCharacter(page, {
      name: data.name,
      description: data.description
    })

    // Should show character
    await expect(page.locator(`text=${data.name}`)).toBeVisible()
  })

  test('should view character details', async ({ page }) => {
    const data = testCharacters.marcus

    await createCharacter(page, data)

    // Click on character to view details
    await page.click(`text=${data.name}`)

    // Should show character details
    await expect(page.locator(`h1:has-text("${data.name}"), h2:has-text("${data.name}")`)).toBeVisible()
    await expect(page.locator(`text=${data.description}`)).toBeVisible()
    await expect(page.locator(`text=${data.personality_traits}`)).toBeVisible()
  })

  test('should edit character information', async ({ page }) => {
    const data = testCharacters.nova

    await createCharacter(page, data)

    // Click edit button
    await page.locator(`text=${data.name}`).locator('..').locator('..').locator('button:has-text("Edit")').click()

    // Update description
    const newDescription = 'Updated: A sentient AI discovering the meaning of consciousness'
    await page.fill('textarea[name="description"], textarea[id="description"]', newDescription)
    await page.click('button:has-text("Save")')

    // Should show updated description
    await expect(page.locator(`text=${newDescription}`)).toBeVisible()
  })

  test('should delete a character', async ({ page }) => {
    const data = generateUniqueTestData().character

    await createCharacter(page, data)

    // Click delete button
    await page.locator(`text=${data.name}`).locator('..').locator('..').locator('button:has-text("Delete")').click()

    // Confirm deletion
    await page.click('button:has-text("Delete Character"), button:has-text("Delete")')

    // Should not show character
    await expect(page.locator(`text=${data.name}`)).not.toBeVisible()
  })

  test('should create multiple characters for a trilogy', async ({ page }) => {
    // Create three characters
    await createCharacter(page, testCharacters.kira)
    await createCharacter(page, testCharacters.marcus)
    await createCharacter(page, testCharacters.nova)

    // Should show all three characters
    await expect(page.locator(`text=${testCharacters.kira.name}`)).toBeVisible()
    await expect(page.locator(`text=${testCharacters.marcus.name}`)).toBeVisible()
    await expect(page.locator(`text=${testCharacters.nova.name}`)).toBeVisible()
  })

  test('should filter/search characters', async ({ page }) => {
    await createCharacter(page, testCharacters.kira)
    await createCharacter(page, testCharacters.marcus)

    // Search for specific character
    const searchBox = page.locator('input[placeholder*="Search"], input[type="search"]')
    if (await searchBox.count() > 0) {
      await searchBox.fill('Kira')

      // Should show only Kira
      await expect(page.locator(`text=${testCharacters.kira.name}`)).toBeVisible()
      await expect(page.locator(`text=${testCharacters.marcus.name}`)).not.toBeVisible()
    }
  })
})

test.describe('Character Embeddings - Epic 5A', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToCharacters(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should show embedding status for character', async ({ page }) => {
    const data = testCharacters.kira

    await createCharacter(page, data)

    // Click on character details
    await page.click(`text=${data.name}`)

    // Should show embedding status or generate button
    const hasEmbeddingStatus = await page.locator('text=/Embedding|Vector|RAG/i').count() > 0
    expect(hasEmbeddingStatus).toBeTruthy()
  })

  test('should generate character embeddings', async ({ page }) => {
    const data = testCharacters.marcus

    await createCharacter(page, data)
    await page.click(`text=${data.name}`)

    // Click generate embeddings button if present
    const generateButton = page.locator('button:has-text("Generate Embeddings"), button:has-text("Embed")')
    if (await generateButton.count() > 0) {
      await generateButton.click()

      // Should show processing state or success message
      await expect(page.locator('text=/Processing|Success|Complete/i')).toBeVisible({ timeout: 10000 })
    }
  })

  test('should regenerate character embeddings', async ({ page }) => {
    const data = testCharacters.nova

    await createCharacter(page, data)
    await page.click(`text=${data.name}`)

    // If regenerate button exists
    const regenerateButton = page.locator('button:has-text("Regenerate"), button:has-text("Re-embed")')
    if (await regenerateButton.count() > 0) {
      await regenerateButton.click()

      // Confirm regeneration
      await page.click('button:has-text("Confirm"), button:has-text("Regenerate")')

      // Should show success
      await expect(page.locator('[role="status"]:has-text("Success")')).toBeVisible({ timeout: 10000 })
    }
  })
})

test.describe('Character Arc Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToCharacters(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should add character arc information', async ({ page }) => {
    const data = testCharacters.kira

    await createCharacter(page, data)
    await page.click(`text=${data.name}`)

    // If arc field exists
    const arcField = page.locator('textarea[name="arc_summary"], textarea[id="arc"]')
    if (await arcField.count() > 0) {
      await arcField.fill(data.arc_summary || 'Character transforms throughout the trilogy')
      await page.click('button:has-text("Save")')

      // Should show success
      await expect(page.locator('[role="status"]:has-text("updated")')).toBeVisible()
    }
  })

  test('should define character motivations', async ({ page }) => {
    const data = testCharacters.marcus

    await createCharacter(page, data)
    await page.click(`text=${data.name}`)

    // If motivations field exists
    const motivationsField = page.locator('textarea[name="motivations"], textarea[id="motivations"]')
    if (await motivationsField.count() > 0) {
      await motivationsField.fill(data.motivations || 'Seeks to understand consciousness')
      await page.click('button:has-text("Save")')

      await expect(page.locator('[role="status"]:has-text("updated")')).toBeVisible()
    }
  })
})
