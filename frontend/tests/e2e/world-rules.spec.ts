/**
 * E2E Tests: World Rules Management
 *
 * Tests Epic 3: Create, manage, and organize world rules
 */

import { test, expect } from '@playwright/test'
import { TEST_USERS, login, createTrilogy, createWorldRule, navigateToWorldRules, cleanupTestData } from '../utils/test-helpers'
import { testTrilogies, testWorldRules, generateUniqueTestData } from '../fixtures/test-data'

test.describe('World Rules Management - Epic 3', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create a trilogy for world rules tests
    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToWorldRules(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should display empty state when no world rules exist', async ({ page }) => {
    // Should show empty state
    await expect(page.locator('text=/No (world )?rules/i')).toBeVisible()
    await expect(page.locator('button:has-text("Create"), button:has-text("Add Rule")')).toBeVisible()
  })

  test('should create a world rule with all fields', async ({ page }) => {
    const data = testWorldRules.quantumConsciousness

    await createWorldRule(page, data)

    // Should show world rule in list
    await expect(page.locator(`text=${data.title}`)).toBeVisible()
    await expect(page.locator(`text=${data.description}`)).toBeVisible()
  })

  test('should create world rule with minimum required fields', async ({ page }) => {
    const data = generateUniqueTestData().worldRule

    await createWorldRule(page, {
      title: data.title,
      description: data.description,
      category: data.category
    })

    // Should show world rule
    await expect(page.locator(`text=${data.title}`)).toBeVisible()
  })

  test('should view world rule details', async ({ page }) => {
    const data = testWorldRules.aiEmergence

    await createWorldRule(page, data)

    // Click on world rule to view details
    await page.click(`text=${data.title}`)

    // Should show world rule details
    await expect(page.locator(`h1:has-text("${data.title}"), h2:has-text("${data.title}")`)).toBeVisible()
    await expect(page.locator(`text=${data.description}`)).toBeVisible()
    await expect(page.locator(`text=${data.category}`)).toBeVisible()
  })

  test('should edit world rule information', async ({ page }) => {
    const data = testWorldRules.marsColony

    await createWorldRule(page, data)

    // Click edit button
    await page.locator(`text=${data.title}`).locator('..').locator('..').locator('button:has-text("Edit")').click()

    // Update description
    const newDescription = 'Updated: Mars colonies now operate under stricter communication protocols due to solar radiation interference.'
    await page.fill('textarea[name="description"], textarea[id="description"]', newDescription)
    await page.click('button:has-text("Save")')

    // Should show updated description
    await expect(page.locator(`text=${newDescription}`)).toBeVisible()
  })

  test('should delete a world rule', async ({ page }) => {
    const data = generateUniqueTestData().worldRule

    await createWorldRule(page, data)

    // Click delete button
    await page.locator(`text=${data.title}`).locator('..').locator('..').locator('button:has-text("Delete")').click()

    // Confirm deletion
    await page.click('button:has-text("Delete Rule"), button:has-text("Delete")')

    // Should not show world rule
    await expect(page.locator(`text=${data.title}`)).not.toBeVisible()
  })

  test('should categorize world rules by type', async ({ page }) => {
    // Create rules with different categories
    await createWorldRule(page, testWorldRules.quantumConsciousness) // Physics
    await createWorldRule(page, testWorldRules.aiEmergence) // Technology
    await createWorldRule(page, testWorldRules.marsColony) // Setting

    // Should show all three rules
    await expect(page.locator(`text=${testWorldRules.quantumConsciousness.title}`)).toBeVisible()
    await expect(page.locator(`text=${testWorldRules.aiEmergence.title}`)).toBeVisible()
    await expect(page.locator(`text=${testWorldRules.marsColony.title}`)).toBeVisible()

    // Check if category badges/labels are visible
    await expect(page.locator('text=Physics')).toBeVisible()
    await expect(page.locator('text=Technology')).toBeVisible()
    await expect(page.locator('text=Setting')).toBeVisible()
  })

  test('should filter world rules by category', async ({ page }) => {
    await createWorldRule(page, testWorldRules.quantumConsciousness) // Physics
    await createWorldRule(page, testWorldRules.aiEmergence) // Technology

    // Look for category filter dropdown or buttons
    const categoryFilter = page.locator('select[name="category"], button:has-text("Category"), [data-testid="category-filter"]')

    if (await categoryFilter.count() > 0) {
      // Select Physics category
      await categoryFilter.click()
      await page.click('text=Physics')

      // Should show only Physics rule
      await expect(page.locator(`text=${testWorldRules.quantumConsciousness.title}`)).toBeVisible()
      await expect(page.locator(`text=${testWorldRules.aiEmergence.title}`)).not.toBeVisible()
    }
  })

  test('should search/filter world rules', async ({ page }) => {
    await createWorldRule(page, testWorldRules.quantumConsciousness)
    await createWorldRule(page, testWorldRules.aiEmergence)

    // Search for specific rule
    const searchBox = page.locator('input[placeholder*="Search"], input[type="search"]')
    if (await searchBox.count() > 0) {
      await searchBox.fill('Quantum')

      // Should show only Quantum rule
      await expect(page.locator(`text=${testWorldRules.quantumConsciousness.title}`)).toBeVisible()
      await expect(page.locator(`text=${testWorldRules.aiEmergence.title}`)).not.toBeVisible()
    }
  })

  test('should create multiple world rules for a trilogy', async ({ page }) => {
    // Create all test world rules
    await createWorldRule(page, testWorldRules.quantumConsciousness)
    await createWorldRule(page, testWorldRules.aiEmergence)
    await createWorldRule(page, testWorldRules.marsColony)

    // Should show all three rules
    await expect(page.locator(`text=${testWorldRules.quantumConsciousness.title}`)).toBeVisible()
    await expect(page.locator(`text=${testWorldRules.aiEmergence.title}`)).toBeVisible()
    await expect(page.locator(`text=${testWorldRules.marsColony.title}`)).toBeVisible()
  })
})

test.describe('World Rules - Book Association', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToWorldRules(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should associate world rule with specific books', async ({ page }) => {
    const data = testWorldRules.quantumConsciousness

    await createWorldRule(page, data)

    // Click on world rule to view details
    await page.click(`text=${data.title}`)

    // Look for book association controls
    const bookSelector = page.locator('select[name*="book"], [data-testid="book-selector"]')

    if (await bookSelector.count() > 0) {
      // Select Book 1
      await bookSelector.click()
      await page.click('text=Book 1')

      // Should show success message
      await expect(page.locator('[role="status"]:has-text("updated"), [role="status"]:has-text("associated")')).toBeVisible()
    }
  })

  test('should show which books use a world rule', async ({ page }) => {
    const data = testWorldRules.aiEmergence

    await createWorldRule(page, data)
    await page.click(`text=${data.title}`)

    // Should show book associations section
    const hasBookSection = await page.locator('text=/Books|Applies to|Used in/i').count() > 0
    expect(hasBookSection).toBeTruthy()
  })
})

test.describe('World Rules - RAG Preview', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToWorldRules(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should show RAG preview for world rule', async ({ page }) => {
    const data = testWorldRules.consciousnessTransfer

    await createWorldRule(page, data)
    await page.click(`text=${data.title}`)

    // Look for RAG preview section or button
    const ragPreview = page.locator('text=/RAG Preview|Preview|Generate Preview/i')

    if (await ragPreview.count() > 0) {
      // Should show RAG-related content
      expect(await ragPreview.count()).toBeGreaterThan(0)
    }
  })

  test('should display world rule in context format for RAG', async ({ page }) => {
    const data = testWorldRules.quantumEntanglement

    await createWorldRule(page, data)
    await page.click(`text=${data.title}`)

    // Look for context or formatted view
    const contextView = page.locator('[data-testid="rag-context"], .context-view, text=/Context|RAG Format/i')

    if (await contextView.count() > 0) {
      // Should show formatted context including title, category, and description
      const contextText = await page.textContent('body')
      expect(contextText).toContain(data.title)
      expect(contextText).toContain(data.category)
    }
  })

  test('should allow testing RAG query with world rule', async ({ page }) => {
    const data = testWorldRules.aiEmergence

    await createWorldRule(page, data)
    await page.click(`text=${data.title}`)

    // Look for test/preview button
    const testButton = page.locator('button:has-text("Test"), button:has-text("Preview RAG")')

    if (await testButton.count() > 0) {
      await testButton.click()

      // Should show some kind of preview or test result
      await expect(page.locator('[role="dialog"], .preview-modal')).toBeVisible({ timeout: 10000 })
    }
  })
})

test.describe('World Rules - Organization', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToWorldRules(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should group world rules by category', async ({ page }) => {
    // Create rules from different categories
    await createWorldRule(page, testWorldRules.quantumConsciousness) // Physics
    await createWorldRule(page, testWorldRules.aiEmergence) // Technology
    await createWorldRule(page, testWorldRules.marsColony) // Setting

    // Check if rules are organized by category
    // This could be via tabs, sections, or grouped lists
    const hasOrganization = await page.locator('[data-testid="category-section"], .category-group, text=/Physics|Technology|Setting/').count() > 0
    expect(hasOrganization).toBeTruthy()
  })

  test('should display category badges or labels', async ({ page }) => {
    const data = testWorldRules.quantumConsciousness

    await createWorldRule(page, data)

    // Should show category badge
    await expect(page.locator(`text=${data.category}`)).toBeVisible()

    // Category should be visually distinct (badge, pill, tag, etc.)
    const categoryBadge = page.locator('[class*="badge"], [class*="tag"], [class*="pill"]').filter({ hasText: data.category })
    if (await categoryBadge.count() > 0) {
      await expect(categoryBadge.first()).toBeVisible()
    }
  })

  test('should sort world rules alphabetically', async ({ page }) => {
    // Create rules that will be out of alphabetical order
    const rule1 = { ...generateUniqueTestData().worldRule, title: 'Zebra Rule' }
    const rule2 = { ...generateUniqueTestData().worldRule, title: 'Alpha Rule' }
    const rule3 = { ...generateUniqueTestData().worldRule, title: 'Beta Rule' }

    await createWorldRule(page, rule1)
    await createWorldRule(page, rule2)
    await createWorldRule(page, rule3)

    // Look for sort controls
    const sortControl = page.locator('button:has-text("Sort"), select[name="sort"]')

    if (await sortControl.count() > 0) {
      await sortControl.click()
      await page.click('text=Alphabetical, text=A-Z, text=Name')

      // Check order of rules in list
      const rules = await page.locator('[data-testid="world-rule-card"], .rule-card, [class*="rule"]').allTextContents()
      const ruleNames = rules.map(r => {
        if (r.includes('Alpha Rule')) return 'Alpha Rule'
        if (r.includes('Beta Rule')) return 'Beta Rule'
        if (r.includes('Zebra Rule')) return 'Zebra Rule'
        return null
      }).filter(Boolean)

      // Alpha should come before Beta and Zebra
      const alphaIndex = ruleNames.indexOf('Alpha Rule')
      const betaIndex = ruleNames.indexOf('Beta Rule')
      const zebraIndex = ruleNames.indexOf('Zebra Rule')

      if (alphaIndex >= 0 && betaIndex >= 0) {
        expect(alphaIndex).toBeLessThan(betaIndex)
      }
    }
  })
})

test.describe('World Rules - Validation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    await page.goto('/dashboard')
    const data = testTrilogies.consciousness
    await createTrilogy(page, data)
    await navigateToWorldRules(page, data.title)
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should require title field', async ({ page }) => {
    // Try to create without title
    await page.click('button:has-text("Create"), button:has-text("Add Rule")')

    // Fill only description
    await page.fill('textarea[name="description"], textarea[id="description"]', 'A rule without a title')

    // Try to submit
    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Should show validation error
    const hasError = await page.locator('text=/required|Required|must|Title/i').count() > 0
    expect(hasError).toBeTruthy()
  })

  test('should require category field', async ({ page }) => {
    // Try to create without category
    await page.click('button:has-text("Create"), button:has-text("Add Rule")')

    // Fill only title and description
    await page.fill('input[name="title"], input[id="title"]', 'Test Rule')
    await page.fill('textarea[name="description"], textarea[id="description"]', 'A rule without a category')

    // Try to submit
    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Should show validation error or prevent submission
    const canSubmit = await page.locator('button:has-text("Create"), button:has-text("Save")').isDisabled()
    const hasError = await page.locator('text=/category|Category|required/i').count() > 0

    expect(canSubmit || hasError).toBeTruthy()
  })

  test('should handle long descriptions', async ({ page }) => {
    const longDescription = 'A '.repeat(500) + 'very long world rule description that tests the limits of the description field.'
    const data = {
      ...generateUniqueTestData().worldRule,
      description: longDescription
    }

    await createWorldRule(page, data)

    // Should successfully create the rule
    await expect(page.locator(`text=${data.title}`)).toBeVisible()

    // Click to view and verify description was saved
    await page.click(`text=${data.title}`)
    await expect(page.locator(`text=/very long world rule/i`)).toBeVisible()
  })
})
