/**
 * E2E Tests: Integration Workflows
 *
 * Tests complete user journeys that span multiple epics and features.
 * These tests validate the entire application flow from start to finish.
 */

import { test, expect } from '@playwright/test'
import { TEST_USERS, login, createTrilogy, createCharacter, createWorldRule, createChapter, setPrimaryTrilogy, navigateToCharacters, cleanupTestData } from '../utils/test-helpers'
import { testTrilogies, testCharacters, testWorldRules, generateUniqueTestData } from '../fixtures/test-data'

test.describe('Complete User Journey: New User Workflow', () => {
  test.afterEach(async ({ page }) => {
    await cleanupTestData(page)
  })

  test('should complete full workflow: trilogy → characters → chapters → content', async ({ page }) => {
    // Step 1: Login
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    // Verify dashboard loaded
    await expect(page.locator('text=Welcome, text=Dashboard')).toBeVisible()

    // Step 2: Create a trilogy
    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    // Verify trilogy created
    await expect(page.locator(`text=${trilogyData.title}`)).toBeVisible()

    // Step 3: Set as primary trilogy
    await setPrimaryTrilogy(page, trilogyData.title)

    // Step 4: Add characters
    await navigateToCharacters(page, trilogyData.title)
    await createCharacter(page, testCharacters.kira)
    await createCharacter(page, testCharacters.marcus)
    await createCharacter(page, testCharacters.nova)

    // Verify all characters created
    await expect(page.locator(`text=${testCharacters.kira.name}`)).toBeVisible()
    await expect(page.locator(`text=${testCharacters.marcus.name}`)).toBeVisible()
    await expect(page.locator(`text=${testCharacters.nova.name}`)).toBeVisible()

    // Step 5: Add world rules
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('button:has-text("World Rules")')
    await createWorldRule(page, testWorldRules.quantumConsciousness)
    await createWorldRule(page, testWorldRules.aiEmergence)

    // Verify world rules created
    await expect(page.locator(`text=${testWorldRules.quantumConsciousness.title}`)).toBeVisible()

    // Step 6: Navigate to Book 1 and create chapters
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')

    await createChapter(page, {
      title: 'Chapter 1: Discovery',
      chapter_plot: 'Kira discovers the quantum anomaly',
      pov_character: testCharacters.kira.name,
      target_word_count: 3000
    })

    await createChapter(page, {
      title: 'Chapter 2: Investigation',
      chapter_plot: 'Marcus analyzes the AI consciousness patterns',
      pov_character: testCharacters.marcus.name,
      target_word_count: 3000
    })

    // Verify chapters created
    await expect(page.locator('text=Chapter 1: Discovery')).toBeVisible()
    await expect(page.locator('text=Chapter 2: Investigation')).toBeVisible()

    // Step 7: Create and generate sub-chapter content
    await page.click('text=Chapter 1: Discovery')

    // Create manual sub-chapter
    const createButton = page.locator('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    if (await createButton.count() > 0) {
      await createButton.click()
      await page.fill('input[name="title"], input[id="title"]', 'Scene 1: The Signal')
      await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Kira detects unusual quantum signatures')

      const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
      if (await contentField.count() > 0) {
        await contentField.fill('Kira stood before the quantum array, her trained eyes scanning the cascading data streams.')
      }

      await page.click('button:has-text("Create"), button:has-text("Save")')

      // Verify sub-chapter created
      await expect(page.locator('text=Scene 1: The Signal')).toBeVisible()
    }

    // Step 8: Verify dashboard shows progress
    await page.goto('/dashboard')

    // Should show primary trilogy with stats
    await expect(page.locator(`text=${trilogyData.title}`)).toBeVisible()
    await expect(page.locator('text=/Chapters|Characters|Words/i')).toBeVisible()
  })
})

test.describe('Multiple Trilogies Management', () => {
  test.afterEach(async ({ page }) => {
    await cleanupTestData(page)
  })

  test('should manage multiple trilogies independently', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    // Create two trilogies
    const trilogy1 = testTrilogies.consciousness
    const trilogy2 = testTrilogies.quantumMinds

    await createTrilogy(page, trilogy1)
    await createTrilogy(page, trilogy2)

    // Verify both exist
    await expect(page.locator(`text=${trilogy1.title}`)).toBeVisible()
    await expect(page.locator(`text=${trilogy2.title}`)).toBeVisible()

    // Add character to first trilogy
    await navigateToCharacters(page, trilogy1.title)
    await createCharacter(page, testCharacters.kira)

    // Add different character to second trilogy
    await page.goto('/dashboard')
    await navigateToCharacters(page, trilogy2.title)
    await createCharacter(page, testCharacters.marcus)

    // Verify characters are in correct trilogies
    await page.goto('/dashboard')
    await navigateToCharacters(page, trilogy1.title)
    await expect(page.locator(`text=${testCharacters.kira.name}`)).toBeVisible()
    await expect(page.locator(`text=${testCharacters.marcus.name}`)).not.toBeVisible()

    await page.goto('/dashboard')
    await navigateToCharacters(page, trilogy2.title)
    await expect(page.locator(`text=${testCharacters.marcus.name}`)).toBeVisible()
    await expect(page.locator(`text=${testCharacters.kira.name}`)).not.toBeVisible()
  })

  test('should switch between trilogies seamlessly', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    // Create two trilogies
    const trilogy1 = generateUniqueTestData().trilogy
    const trilogy2 = generateUniqueTestData().trilogy

    await createTrilogy(page, trilogy1)
    await createTrilogy(page, trilogy2)

    // Work on first trilogy
    await page.click(`text=${trilogy1.title}`)
    await expect(page.locator(`h1:has-text("${trilogy1.title}")`)).toBeVisible()

    // Switch to second trilogy
    await page.goto('/dashboard')
    await page.click(`text=${trilogy2.title}`)
    await expect(page.locator(`h1:has-text("${trilogy2.title}")`)).toBeVisible()

    // Switch back to first
    await page.goto('/dashboard')
    await page.click(`text=${trilogy1.title}`)
    await expect(page.locator(`h1:has-text("${trilogy1.title}")`)).toBeVisible()
  })

  test('should track progress across multiple books', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)
    await setPrimaryTrilogy(page, trilogyData.title)

    // Add character
    await navigateToCharacters(page, trilogyData.title)
    await createCharacter(page, testCharacters.kira)

    // Create chapter in Book 1
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Book 1 - Chapter 1',
      chapter_plot: 'First chapter',
      pov_character: testCharacters.kira.name
    })

    // Create chapter in Book 2
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 2')

    const createButton = page.locator('button:has-text("Create"), button:has-text("Add Chapter")')
    if (await createButton.count() > 0) {
      await createChapter(page, {
        title: 'Book 2 - Chapter 1',
        chapter_plot: 'Second book begins',
        pov_character: testCharacters.kira.name
      })
    }

    // View trilogy details to see overall progress
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)

    // Should show book progress
    await expect(page.locator('text=Book 1')).toBeVisible()
    await expect(page.locator('text=Book 2')).toBeVisible()
  })
})

test.describe('Content Generation Workflows', () => {
  test.afterEach(async ({ page }) => {
    await cleanupTestData(page)
  })

  test('should generate content using specific world rules', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    // Setup: Create trilogy with character and world rules
    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    await navigateToCharacters(page, trilogyData.title)
    await createCharacter(page, testCharacters.kira)

    // Create multiple world rules
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('button:has-text("World Rules")')
    await createWorldRule(page, testWorldRules.quantumConsciousness)
    await createWorldRule(page, testWorldRules.marsColony)

    // Create chapter
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Chapter 1: Mars Discovery',
      chapter_plot: 'Kira discovers quantum phenomena on Mars',
      pov_character: testCharacters.kira.name
    })

    await page.click('text=Chapter 1: Mars Discovery')

    // Generate sub-chapter with specific world rules
    const generateButton = page.locator('button:has-text("Generate"), button:has-text("AI Generate")')
    if (await generateButton.count() > 0) {
      await generateButton.click()
      await page.fill('input[name="title"], input[id="title"]', 'Generated Scene: Mars Observation')

      const plotField = page.locator('textarea[name="plot_points"], textarea[id="plot"]')
      if (await plotField.count() > 0) {
        await plotField.fill('Kira observes quantum consciousness patterns while dealing with Mars colony constraints')
      }

      // Select both world rules if available
      const quantumRule = page.locator(`input[type="checkbox"]:near(:text("${testWorldRules.quantumConsciousness.title}"))`)
      const marsRule = page.locator(`input[type="checkbox"]:near(:text("${testWorldRules.marsColony.title}"))`)

      if (await quantumRule.count() > 0) {
        await quantumRule.check()
      }
      if (await marsRule.count() > 0) {
        await marsRule.check()
      }

      // Start generation
      await page.click('button:has-text("Generate"), button:has-text("Start Generation")')

      // Wait for completion
      await expect(page.locator('text=/Generating|Processing/i')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('text=/Complete|Success/i')).toBeVisible({ timeout: 60000 })
    }
  })

  test('should review and edit generated content', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    // Setup trilogy, character, chapter
    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    await navigateToCharacters(page, trilogyData.title)
    await createCharacter(page, testCharacters.kira)

    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Chapter 1',
      chapter_plot: 'Test chapter',
      pov_character: testCharacters.kira.name
    })

    await page.click('text=Chapter 1')

    // Create a sub-chapter with content
    const createButton = page.locator('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    if (await createButton.count() > 0) {
      await createButton.click()
      await page.fill('input[name="title"], input[id="title"]', 'Editable Scene')
      await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Original plot')

      const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
      if (await contentField.count() > 0) {
        await contentField.fill('Original generated content that needs editing.')
        await page.click('button:has-text("Create"), button:has-text("Save")')

        // Review the content
        await page.click('text=Editable Scene')
        await expect(page.locator('text=Original generated content')).toBeVisible()

        // Edit the content
        await page.click('button:has-text("Edit")')
        await contentField.fill('Edited and improved content with better flow and detail.')
        await page.click('button:has-text("Save")')

        // Verify changes saved
        await expect(page.locator('text=Edited and improved content')).toBeVisible()
      }
    }
  })

  test('should track progress and word counts across workflow', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)
    await setPrimaryTrilogy(page, trilogyData.title)

    await navigateToCharacters(page, trilogyData.title)
    await createCharacter(page, testCharacters.kira)

    // Create chapter with target
    await page.goto('/dashboard')
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Chapter 1',
      chapter_plot: 'Test chapter',
      pov_character: testCharacters.kira.name,
      target_word_count: 3000
    })

    // Create sub-chapter with content
    await page.click('text=Chapter 1')

    const createButton = page.locator('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    if (await createButton.count() > 0) {
      await createButton.click()
      await page.fill('input[name="title"], input[id="title"]', 'Scene 1')
      await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Plot')

      const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
      if (await contentField.count() > 0) {
        // Add content with ~50 words
        await contentField.fill('This is a test scene with some content. ' + 'Word '.repeat(40) + 'End.')
        await page.click('button:has-text("Create"), button:has-text("Save")')
      }
    }

    // Check progress tracking in dashboard
    await page.goto('/dashboard')

    // Should show word count progress
    await expect(page.locator('text=/Words|Progress|[0-9]+%/i')).toBeVisible()
  })
})

test.describe('Cross-Feature Integration', () => {
  test.afterEach(async ({ page }) => {
    await cleanupTestData(page)
  })

  test('should maintain consistency across all features', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    const trilogyData = generateUniqueTestData().trilogy

    // Create trilogy
    await createTrilogy(page, trilogyData)

    // Verify in dashboard
    await expect(page.locator(`text=${trilogyData.title}`)).toBeVisible()

    // Update trilogy description
    await page.click(`text=${trilogyData.title}`)
    const editButton = page.locator('button:has-text("Edit"):near(:text("Narrative"))')
    if (await editButton.count() > 0) {
      await editButton.click()
      const newDescription = 'Updated narrative overview'
      await page.fill('textarea[name="narrative_overview"], textarea[id="edit-description"]', newDescription)
      await page.click('button:has-text("Save")')

      // Verify update persists
      await expect(page.locator(`text=${newDescription}`)).toBeVisible()

      // Go back to dashboard and verify
      await page.goto('/dashboard')
      await page.click(`text=${trilogyData.title}`)
      await expect(page.locator(`text=${newDescription}`)).toBeVisible()
    }
  })

  test('should handle navigation across all levels', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    await navigateToCharacters(page, trilogyData.title)
    await createCharacter(page, testCharacters.kira)

    // Navigate: Dashboard → Trilogy → Book → Chapter → Sub-Chapter
    await page.goto('/dashboard')
    await expect(page.locator(`text=${trilogyData.title}`)).toBeVisible()

    await page.click(`text=${trilogyData.title}`)
    await expect(page.locator('text=Book 1')).toBeVisible()

    await page.click('text=Book 1')

    // Create chapter
    const hasChapters = await page.locator('button:has-text("Create"), button:has-text("Add Chapter")').count() > 0
    if (hasChapters) {
      await createChapter(page, {
        title: 'Navigation Test Chapter',
        chapter_plot: 'Testing navigation',
        pov_character: testCharacters.kira.name
      })

      await page.click('text=Navigation Test Chapter')

      // Verify we're at chapter level
      await expect(page.locator('h1:has-text("Navigation Test Chapter"), h2:has-text("Navigation Test Chapter")')).toBeVisible()

      // Navigate back using breadcrumbs or back button
      const backNav = page.locator('text=Back, a:has-text("Book 1"), [data-testid="breadcrumb"]')
      if (await backNav.count() > 0) {
        await backNav.first().click()
        await expect(page.locator('text=Book 1')).toBeVisible()
      }
    }
  })

  test('should support quick actions from dashboard', async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)
    await page.goto('/dashboard')

    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)
    await setPrimaryTrilogy(page, trilogyData.title)

    await page.goto('/dashboard')

    // Should show primary trilogy with quick actions
    await expect(page.locator('button:has-text("Characters")')).toBeVisible()
    await expect(page.locator('button:has-text("World Rules")')).toBeVisible()

    // Use quick action to navigate to characters
    await page.click('button:has-text("Characters")')

    // Should navigate directly to characters page
    await expect(page).toHaveURL(/\/characters$/)
  })
})
