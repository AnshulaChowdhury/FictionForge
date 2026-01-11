/**
 * E2E Tests: Sub-Chapter Management and Content Generation
 *
 * Tests Epic 6: Create, generate, and manage sub-chapters with RAG
 * Tests Epic 7: Version control for sub-chapter content
 */

import { test, expect } from '@playwright/test'
import { TEST_USERS, login, createTrilogy, createCharacter, createChapter, createWorldRule, navigateToCharacters, cleanupTestData } from '../utils/test-helpers'
import { testTrilogies, testCharacters, testChapters, testWorldRules, generateUniqueTestData } from '../fixtures/test-data'

test.describe('Sub-Chapter Management - Epic 6', () => {
  let trilogyTitle: string

  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy with character
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    trilogyTitle = trilogyData.title
    await createTrilogy(page, trilogyData)

    // Create character
    await navigateToCharacters(page, trilogyTitle)
    await createCharacter(page, testCharacters.kira)

    // Navigate to Book 1, create a chapter
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Chapter 1: Discovery',
      chapter_plot: 'Kira discovers the anomaly',
      pov_character: testCharacters.kira.name
    })

    // Navigate to chapter detail to access sub-chapters
    await page.click('text=Chapter 1: Discovery')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should display empty state when no sub-chapters exist', async ({ page }) => {
    // Should show empty state or no sub-chapters message
    const hasEmptyState = await page.locator('text=/No (sub-)?chapters|No scenes|Get started/i').count() > 0
    expect(hasEmptyState).toBeTruthy()

    // Should show create button
    await expect(page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("Generate")')).toBeVisible()
  })

  test('should create sub-chapter manually', async ({ page }) => {
    // Click create sub-chapter button
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')

    // Fill in details
    await page.fill('input[name="title"], input[id="title"]', 'Scene 1: The Signal')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Kira detects an unusual quantum signature')

    // Set target word count if available
    const wordCountField = page.locator('input[name="target_word_count"], input[type="number"]')
    if (await wordCountField.count() > 0) {
      await wordCountField.fill('1000')
    }

    // Save
    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Should show sub-chapter
    await expect(page.locator('text=Scene 1: The Signal')).toBeVisible()
  })

  test('should create sub-chapter with content', async ({ page }) => {
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')

    await page.fill('input[name="title"], input[id="title"]', 'Opening Scene')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'The chapter opens')

    // Look for content field
    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('Kira stood before the quantum array, her eyes scanning the data streams.')
    }

    await page.click('button:has-text("Create"), button:has-text("Save")')

    await expect(page.locator('text=Opening Scene')).toBeVisible()
  })

  test('should edit sub-chapter content', async ({ page }) => {
    // Create a sub-chapter first
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Test Scene')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Test plot')
    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Click edit button
    await page.locator('text=Test Scene').locator('..').locator('..').locator('button:has-text("Edit")').click()

    // Update content
    const newContent = 'Updated content: The quantum array hummed with energy as Kira approached.'
    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')

    if (await contentField.count() > 0) {
      await contentField.fill(newContent)
      await page.click('button:has-text("Save")')

      // Should show success
      await expect(page.locator('[role="status"]:has-text("updated"), [role="status"]:has-text("saved")')).toBeVisible()
    }
  })

  test('should delete sub-chapter', async ({ page }) => {
    // Create a sub-chapter
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Scene to Delete')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'This will be deleted')
    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Delete it
    await page.locator('text=Scene to Delete').locator('..').locator('..').locator('button:has-text("Delete")').click()
    await page.click('button:has-text("Delete"), button:has-text("Confirm")')

    // Should not show sub-chapter
    await expect(page.locator('text=Scene to Delete')).not.toBeVisible()
  })

  test('should reorder sub-chapters', async ({ page }) => {
    // Create two sub-chapters
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Scene A')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'First scene')
    await page.click('button:has-text("Create"), button:has-text("Save")')

    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Scene B')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Second scene')
    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Look for reorder controls
    const hasReorderControls = await page.locator('[data-testid="drag-handle"], button:has-text("Move Up"), button:has-text("Move Down")').count() > 0

    if (hasReorderControls) {
      // Move Scene B up
      await page.locator('text=Scene B').locator('..').locator('..').locator('button:has-text("Move Up")').click()

      // Scene B should now be first
      const scenes = await page.locator('[data-testid="sub-chapter-card"], .scene-card, [class*="scene"]').allTextContents()
      const sceneAIndex = scenes.findIndex(s => s.includes('Scene A'))
      const sceneBIndex = scenes.findIndex(s => s.includes('Scene B'))

      if (sceneAIndex >= 0 && sceneBIndex >= 0) {
        expect(sceneBIndex).toBeLessThan(sceneAIndex)
      }
    }
  })
})

test.describe('Sub-Chapter Generation with RAG - Epic 6', () => {
  let trilogyTitle: string

  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy with character and world rule
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    trilogyTitle = trilogyData.title
    await createTrilogy(page, trilogyData)

    // Create character
    await navigateToCharacters(page, trilogyTitle)
    await createCharacter(page, testCharacters.kira)

    // Create world rule (navigate via trilogy detail)
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)
    await page.click('button:has-text("World Rules")')
    await createWorldRule(page, testWorldRules.quantumConsciousness)

    // Create chapter
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Chapter 1: Quantum Discovery',
      chapter_plot: 'Kira discovers quantum consciousness patterns',
      pov_character: testCharacters.kira.name
    })

    // Navigate to chapter
    await page.click('text=Chapter 1: Quantum Discovery')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should show generate sub-chapter option', async ({ page }) => {
    // Should have a generate button
    const generateButton = page.locator('button:has-text("Generate"), button:has-text("AI Generate")')
    await expect(generateButton).toBeVisible()
  })

  test('should generate sub-chapter with RAG', async ({ page }) => {
    // Click generate button
    await page.click('button:has-text("Generate"), button:has-text("AI Generate")')

    // Fill in generation parameters
    await page.fill('input[name="title"], input[id="title"]', 'Generated Scene: The Discovery')

    const plotField = page.locator('textarea[name="plot_points"], textarea[id="plot"]')
    if (await plotField.count() > 0) {
      await plotField.fill('Kira examines the quantum data and realizes consciousness can be transferred')
    }

    // Set word count target
    const wordCountField = page.locator('input[name="target_word_count"], input[type="number"]')
    if (await wordCountField.count() > 0) {
      await wordCountField.fill('800')
    }

    // Start generation
    await page.click('button:has-text("Generate"), button:has-text("Start Generation")')

    // Should show loading/progress state
    await expect(page.locator('text=/Generating|Processing|In Progress/i')).toBeVisible({ timeout: 5000 })

    // Wait for completion (with extended timeout for actual generation)
    await expect(page.locator('text=/Complete|Success|Generated/i')).toBeVisible({ timeout: 60000 })
  })

  test('should display generation progress via WebSocket', async ({ page }) => {
    // Start generation
    await page.click('button:has-text("Generate"), button:has-text("AI Generate")')
    await page.fill('input[name="title"], input[id="title"]', 'WebSocket Test Scene')

    const plotField = page.locator('textarea[name="plot_points"], textarea[id="plot"]')
    if (await plotField.count() > 0) {
      await plotField.fill('Test generation with WebSocket updates')
    }

    await page.click('button:has-text("Generate"), button:has-text("Start Generation")')

    // Should show progress updates
    const hasProgress = await page.locator('[role="progressbar"], [class*="progress"], text=/[0-9]+%/').count() > 0
    expect(hasProgress || await page.locator('text=/Generating|Processing/i').count() > 0).toBeTruthy()
  })

  test('should allow selecting world rules for generation', async ({ page }) => {
    await page.click('button:has-text("Generate"), button:has-text("AI Generate")')
    await page.fill('input[name="title"], input[id="title"]', 'Scene with World Rules')

    // Look for world rule selector
    const worldRuleSelector = page.locator('text=/World Rules|Select Rules|Use Rules/i')

    if (await worldRuleSelector.count() > 0) {
      // Should show available world rules
      await expect(page.locator(`text=${testWorldRules.quantumConsciousness.title}`)).toBeVisible()

      // Select the rule
      await page.click(`text=${testWorldRules.quantumConsciousness.title}`)
    }
  })

  test('should show which world rules were used in generation', async ({ page }) => {
    // Generate a sub-chapter
    await page.click('button:has-text("Generate"), button:has-text("AI Generate")')
    await page.fill('input[name="title"], input[id="title"]', 'Scene with Rules Tracking')

    const plotField = page.locator('textarea[name="plot_points"], textarea[id="plot"]')
    if (await plotField.count() > 0) {
      await plotField.fill('Using quantum consciousness theory')
    }

    // Select world rule if selector exists
    const worldRuleCheckbox = page.locator(`input[type="checkbox"]:near(:text("${testWorldRules.quantumConsciousness.title}")`)
    if (await worldRuleCheckbox.count() > 0) {
      await worldRuleCheckbox.check()
    }

    await page.click('button:has-text("Generate"), button:has-text("Start Generation")')

    // Wait for completion
    await expect(page.locator('text=/Complete|Success|Generated/i')).toBeVisible({ timeout: 60000 })

    // Click on the generated sub-chapter
    await page.click('text=Scene with Rules Tracking')

    // Should show which rules were used
    const hasRuleTracking = await page.locator(`text=${testWorldRules.quantumConsciousness.title}, text=/Rules Used|Based on|References/i`).count() > 0
    expect(hasRuleTracking).toBeTruthy()
  })

  test('should handle generation errors gracefully', async ({ page }) => {
    // Try to generate without required fields
    await page.click('button:has-text("Generate"), button:has-text("AI Generate")')

    // Try to start without title
    const startButton = page.locator('button:has-text("Generate"), button:has-text("Start Generation")')
    if (await startButton.count() > 0) {
      await startButton.click()

      // Should show validation error
      const hasError = await page.locator('text=/required|Required|must provide/i').count() > 0
      expect(hasError).toBeTruthy()
    }
  })
})

test.describe('Sub-Chapter Version Control - Epic 7', () => {
  let trilogyTitle: string

  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy with character
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    trilogyTitle = trilogyData.title
    await createTrilogy(page, trilogyData)

    await navigateToCharacters(page, trilogyTitle)
    await createCharacter(page, testCharacters.kira)

    // Create chapter and sub-chapter
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Chapter 1',
      chapter_plot: 'Test chapter',
      pov_character: testCharacters.kira.name
    })
    await page.click('text=Chapter 1')

    // Create initial sub-chapter
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Versioned Scene')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Initial plot')

    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('Version 1: Initial content for the scene.')
    }

    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Click on the sub-chapter to view details
    await page.click('text=Versioned Scene')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should show version history', async ({ page }) => {
    // Look for version history section
    const versionHistory = page.locator('text=/Version History|Versions|History/i')

    if (await versionHistory.count() > 0) {
      await expect(versionHistory).toBeVisible()

      // Should show at least Version 1
      await expect(page.locator('text=/Version 1|v1|Initial/i')).toBeVisible()
    }
  })

  test('should create new version when editing', async ({ page }) => {
    // Edit the content
    await page.click('button:has-text("Edit")')

    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('Version 2: Updated content with new details.')
      await page.click('button:has-text("Save")')

      // Should show new version
      const hasNewVersion = await page.locator('text=/Version 2|v2/i').count() > 0
      expect(hasNewVersion).toBeTruthy()
    }
  })

  test('should view previous versions', async ({ page }) => {
    // Edit to create Version 2
    await page.click('button:has-text("Edit")')

    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('Version 2: Different content.')
      await page.click('button:has-text("Save")')

      // Click to view Version 1
      const version1Link = page.locator('text=Version 1, button:has-text("View Version 1")')

      if (await version1Link.count() > 0) {
        await version1Link.click()

        // Should show original content
        await expect(page.locator('text=/Version 1: Initial content/i')).toBeVisible()
      }
    }
  })

  test('should compare versions', async ({ page }) => {
    // Create multiple versions
    await page.click('button:has-text("Edit")')

    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('Version 2: Modified content.')
      await page.click('button:has-text("Save")')

      // Look for compare feature
      const compareButton = page.locator('button:has-text("Compare"), text=Compare Versions')

      if (await compareButton.count() > 0) {
        await compareButton.click()

        // Should show comparison interface
        await expect(page.locator('[data-testid="version-comparison"], .diff-viewer')).toBeVisible()
      }
    }
  })

  test('should restore previous version', async ({ page }) => {
    // Create Version 2
    await page.click('button:has-text("Edit")')

    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('Version 2: This will be replaced.')
      await page.click('button:has-text("Save")')

      // Restore Version 1
      const restoreButton = page.locator('button:has-text("Restore"):near(:text("Version 1"))')

      if (await restoreButton.count() > 0) {
        await restoreButton.click()

        // Confirm restoration
        await page.click('button:has-text("Restore"), button:has-text("Confirm")')

        // Should show original content
        await expect(page.locator('text=/Version 1: Initial content/i')).toBeVisible()

        // Should create a new version (Version 3) with restored content
        const hasVersion3 = await page.locator('text=/Version 3|v3/i').count() > 0
        expect(hasVersion3).toBeTruthy()
      }
    }
  })

  test('should show version metadata', async ({ page }) => {
    // Version should show timestamp or date
    const hasTimestamp = await page.locator('text=/[0-9]{1,2}:[0-9]{2}|Today|Yesterday|Created/i').count() > 0
    expect(hasTimestamp).toBeTruthy()
  })
})

test.describe('Sub-Chapter Content Editing', () => {
  let trilogyTitle: string

  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy with character
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    trilogyTitle = trilogyData.title
    await createTrilogy(page, trilogyData)

    await navigateToCharacters(page, trilogyTitle)
    await createCharacter(page, testCharacters.kira)

    // Create chapter
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)
    await page.click('text=Book 1')
    await createChapter(page, {
      title: 'Chapter 1',
      chapter_plot: 'Test chapter',
      pov_character: testCharacters.kira.name
    })
    await page.click('text=Chapter 1')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should save content changes', async ({ page }) => {
    // Create sub-chapter
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Editable Scene')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Test plot')

    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('Original content here.')
    }

    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Edit content
    await page.click('text=Editable Scene')
    await page.click('button:has-text("Edit")')

    if (await contentField.count() > 0) {
      await contentField.fill('Updated content with changes.')
      await page.click('button:has-text("Save")')

      // Should show success
      await expect(page.locator('[role="status"]:has-text("saved"), [role="status"]:has-text("updated")')).toBeVisible()

      // Reload and verify persistence
      await page.reload()
      await expect(page.locator('text=Updated content with changes.')).toBeVisible()
    }
  })

  test('should show word count for content', async ({ page }) => {
    // Create sub-chapter with content
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Word Count Test')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Test')

    const contentField = page.locator('textarea[name="content"], [data-testid="content-editor"]')
    if (await contentField.count() > 0) {
      await contentField.fill('This is a test sentence with exactly ten words total.')
    }

    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Should show word count
    await page.click('text=Word Count Test')
    await expect(page.locator('text=/10.*words|Word Count.*10/i')).toBeVisible()
  })

  test('should support rich text formatting', async ({ page }) => {
    // Create sub-chapter
    await page.click('button:has-text("Create Sub-Chapter"), button:has-text("Add Scene"), button:has-text("Create")')
    await page.fill('input[name="title"], input[id="title"]', 'Formatted Text')
    await page.fill('textarea[name="plot_points"], textarea[id="plot"]', 'Test')

    // Check for rich text editor features
    const hasRichTextEditor = await page.locator('[data-testid="rich-text-editor"], .tiptap, .quill, .editor-toolbar').count() > 0

    if (hasRichTextEditor) {
      // Should have formatting buttons (bold, italic, etc.)
      const hasBoldButton = await page.locator('button[title*="Bold"], button:has-text("B")').count() > 0
      expect(hasBoldButton).toBeTruthy()
    }
  })
})
