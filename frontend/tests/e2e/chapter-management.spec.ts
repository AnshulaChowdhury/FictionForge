/**
 * E2E Tests: Chapter Management
 *
 * Tests Epic 4: Create, organize, and manage chapters with POV characters
 */

import { test, expect } from '@playwright/test'
import { TEST_USERS, login, createTrilogy, createCharacter, createChapter, navigateToCharacters, cleanupTestData } from '../utils/test-helpers'
import { testTrilogies, testCharacters, testChapters, generateUniqueTestData } from '../fixtures/test-data'

test.describe('Chapter Management - Epic 4', () => {
  let trilogyTitle: string
  let bookId: string

  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy and characters
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    trilogyTitle = trilogyData.title
    await createTrilogy(page, trilogyData)

    // Create a character for POV assignment
    await navigateToCharacters(page, trilogyTitle)
    await createCharacter(page, testCharacters.kira)

    // Navigate to trilogy detail to access chapters
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)

    // Click on Book 1 to navigate to chapters
    await page.click('text=Book 1')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should display empty state when no chapters exist', async ({ page }) => {
    // Should show empty state
    await expect(page.locator('text=/No chapters/i')).toBeVisible()
    await expect(page.locator('button:has-text("Create"), button:has-text("Add Chapter")')).toBeVisible()
  })

  test('should create chapter with POV character', async ({ page }) => {
    const data = testChapters.chapter1

    await createChapter(page, {
      title: data.title,
      chapter_plot: data.chapter_plot,
      pov_character: testCharacters.kira.name
    })

    // Should show chapter in list
    await expect(page.locator(`text=${data.title}`)).toBeVisible()

    // Should show POV character
    await expect(page.locator(`text=${testCharacters.kira.name}`)).toBeVisible()
  })

  test('should create chapter with plot notes', async ({ page }) => {
    const data = generateUniqueTestData().chapter

    await createChapter(page, {
      title: data.title,
      chapter_plot: data.plot_notes
    })

    // Should show chapter
    await expect(page.locator(`text=${data.title}`)).toBeVisible()

    // Click to view details
    await page.click(`text=${data.title}`)

    // Should show plot notes
    await expect(page.locator(`text=${data.plot_notes}`)).toBeVisible()
  })

  test('should create chapter with target word count', async ({ page }) => {
    const data = {
      ...generateUniqueTestData().chapter,
      target_word_count: 5000
    }

    await createChapter(page, data)

    // Should show chapter
    await expect(page.locator(`text=${data.title}`)).toBeVisible()

    // Click to view details
    await page.click(`text=${data.title}`)

    // Should show target word count
    await expect(page.locator('text=5000, text=5,000')).toBeVisible()
  })

  test('should create chapter with all fields', async ({ page }) => {
    const data = {
      title: 'Chapter 1: The Awakening',
      chapter_plot: 'Kira discovers an anomalous signal from the quantum array that suggests consciousness patterns.',
      pov_character: testCharacters.kira.name,
      target_word_count: 3500
    }

    await createChapter(page, data)

    // Should show chapter with all details
    await expect(page.locator(`text=${data.title}`)).toBeVisible()

    // Click to view full details
    await page.click(`text=${data.title}`)

    await expect(page.locator(`text=${testCharacters.kira.name}`)).toBeVisible()
    await expect(page.locator(`text=${data.chapter_plot}`)).toBeVisible()
  })

  test('should edit chapter details', async ({ page }) => {
    const data = testChapters.chapter1

    await createChapter(page, data)

    // Click edit button
    await page.locator(`text=${data.title}`).locator('..').locator('..').locator('button:has-text("Edit")').click()

    // Update plot notes
    const newPlot = 'Updated: Kira investigates the quantum anomaly and makes a startling discovery about consciousness transfer.'
    await page.fill('textarea[name="chapter_plot"], textarea[id="plot"], textarea[id="chapter_plot"]', newPlot)
    await page.click('button:has-text("Save")')

    // Should show updated plot
    await expect(page.locator(`text=/Updated: Kira investigates/i`)).toBeVisible()
  })

  test('should delete a chapter', async ({ page }) => {
    const data = generateUniqueTestData().chapter

    await createChapter(page, data)

    // Click delete button
    await page.locator(`text=${data.title}`).locator('..').locator('..').locator('button:has-text("Delete")').click()

    // Confirm deletion
    await page.click('button:has-text("Delete Chapter"), button:has-text("Delete")')

    // Should not show chapter
    await expect(page.locator(`text=${data.title}`)).not.toBeVisible()
  })

  test('should assign POV character to chapter', async ({ page }) => {
    const data = generateUniqueTestData().chapter

    // Create chapter without POV first
    await createChapter(page, {
      title: data.title,
      chapter_plot: data.plot_notes
    })

    // Click to view/edit chapter
    await page.click(`text=${data.title}`)

    // Look for POV character selector
    const povSelector = page.locator('select[name="character_id"], select[name="pov"], [data-testid="pov-selector"]')

    if (await povSelector.count() > 0) {
      await povSelector.click()
      await page.click(`text=${testCharacters.kira.name}`)

      // Should show success
      await expect(page.locator('[role="status"]:has-text("updated")')).toBeVisible()
    }
  })

  test('should change POV character', async ({ page }) => {
    // Create second character
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)
    await page.click('button:has-text("Characters")')
    await createCharacter(page, testCharacters.marcus)

    // Navigate back to chapters
    await page.goto('/dashboard')
    await page.click(`text=${trilogyTitle}`)
    await page.click('text=Book 1')

    // Create chapter with first character
    const data = {
      ...generateUniqueTestData().chapter,
      pov_character: testCharacters.kira.name
    }
    await createChapter(page, data)

    // Click to edit chapter
    await page.click(`text=${data.title}`)

    // Change POV to second character
    const povSelector = page.locator('select[name="character_id"], select[name="pov"], [data-testid="pov-selector"]')

    if (await povSelector.count() > 0) {
      await povSelector.click()
      await page.click(`text=${testCharacters.marcus.name}`)

      // Should show new POV character
      await expect(page.locator(`text=${testCharacters.marcus.name}`)).toBeVisible()
    }
  })

  test('should create multiple chapters in order', async ({ page }) => {
    // Create three chapters
    await createChapter(page, { title: 'Chapter 1: Beginning', chapter_plot: 'The story begins' })
    await createChapter(page, { title: 'Chapter 2: Rising Action', chapter_plot: 'Tension builds' })
    await createChapter(page, { title: 'Chapter 3: Climax', chapter_plot: 'The peak moment' })

    // Should show all chapters
    await expect(page.locator('text=Chapter 1: Beginning')).toBeVisible()
    await expect(page.locator('text=Chapter 2: Rising Action')).toBeVisible()
    await expect(page.locator('text=Chapter 3: Climax')).toBeVisible()

    // Chapters should have numbers 1, 2, 3
    await expect(page.locator('text=/Chapter 1|^1$/i')).toBeVisible()
    await expect(page.locator('text=/Chapter 2|^2$/i')).toBeVisible()
    await expect(page.locator('text=/Chapter 3|^3$/i')).toBeVisible()
  })
})

test.describe('Chapter Progress Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    // Navigate to Book 1 chapters
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should display chapter progress metrics', async ({ page }) => {
    const data = {
      ...generateUniqueTestData().chapter,
      target_word_count: 3000
    }

    await createChapter(page, data)

    // Click to view chapter details
    await page.click(`text=${data.title}`)

    // Should show progress indicators
    await expect(page.locator('text=/Word Count|Words|Progress/i')).toBeVisible()
  })

  test('should show word count and target', async ({ page }) => {
    const data = {
      title: 'Chapter with Target',
      chapter_plot: 'A test chapter',
      target_word_count: 5000
    }

    await createChapter(page, data)
    await page.click(`text=${data.title}`)

    // Should show target word count
    await expect(page.locator('text=/5000|5,000/i')).toBeVisible()

    // Should show current word count (likely 0)
    await expect(page.locator('text=/0.*words|current.*0/i')).toBeVisible()
  })

  test('should display progress percentage', async ({ page }) => {
    const data = {
      ...generateUniqueTestData().chapter,
      target_word_count: 2000
    }

    await createChapter(page, data)
    await page.click(`text=${data.title}`)

    // Should show progress (0% initially)
    const hasProgress = await page.locator('text=/0%|Progress: 0/i, [role="progressbar"]').count() > 0
    expect(hasProgress).toBeTruthy()
  })
})

test.describe('Chapter Organization', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    // Navigate to Book 1 chapters
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should display chapters in order', async ({ page }) => {
    // Create chapters
    await createChapter(page, { title: 'Chapter 1', chapter_plot: 'First' })
    await createChapter(page, { title: 'Chapter 2', chapter_plot: 'Second' })
    await createChapter(page, { title: 'Chapter 3', chapter_plot: 'Third' })

    // Get all chapter elements
    const chapters = await page.locator('[data-testid="chapter-card"], .chapter-card, [class*="chapter"]').allTextContents()

    // Check that Chapter 1 appears before Chapter 2, which appears before Chapter 3
    const chapter1Index = chapters.findIndex(c => c.includes('Chapter 1'))
    const chapter2Index = chapters.findIndex(c => c.includes('Chapter 2'))
    const chapter3Index = chapters.findIndex(c => c.includes('Chapter 3'))

    if (chapter1Index >= 0 && chapter2Index >= 0 && chapter3Index >= 0) {
      expect(chapter1Index).toBeLessThan(chapter2Index)
      expect(chapter2Index).toBeLessThan(chapter3Index)
    }
  })

  test('should show chapter numbers', async ({ page }) => {
    await createChapter(page, { title: 'The Beginning', chapter_plot: 'First chapter' })
    await createChapter(page, { title: 'The Journey', chapter_plot: 'Second chapter' })

    // Should show chapter numbers
    await expect(page.locator('text=/Chapter 1|^1$/i')).toBeVisible()
    await expect(page.locator('text=/Chapter 2|^2$/i')).toBeVisible()
  })

  test('should support reordering chapters', async ({ page }) => {
    // Create chapters
    await createChapter(page, { title: 'Chapter A', chapter_plot: 'First' })
    await createChapter(page, { title: 'Chapter B', chapter_plot: 'Second' })

    // Look for reorder controls (drag handles, up/down buttons)
    const hasReorderControls = await page.locator('[data-testid="drag-handle"], button:has-text("Move Up"), button:has-text("Move Down")').count() > 0

    if (hasReorderControls) {
      // Try to move Chapter B up
      await page.locator('text=Chapter B').locator('..').locator('..').locator('button:has-text("Move Up")').click()

      // Chapter B should now appear before Chapter A
      const chapters = await page.locator('[data-testid="chapter-card"], .chapter-card').allTextContents()
      const chapterAIndex = chapters.findIndex(c => c.includes('Chapter A'))
      const chapterBIndex = chapters.findIndex(c => c.includes('Chapter B'))

      if (chapterAIndex >= 0 && chapterBIndex >= 0) {
        expect(chapterBIndex).toBeLessThan(chapterAIndex)
      }
    }
  })
})

test.describe('Chapter Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    // Navigate to Book 1 chapters
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should navigate to chapter detail page', async ({ page }) => {
    const data = generateUniqueTestData().chapter

    await createChapter(page, data)

    // Click on chapter
    await page.click(`text=${data.title}`)

    // Should navigate to chapter detail page
    await expect(page).toHaveURL(/\/chapter\/[a-f0-9-]+$/)

    // Should show chapter title
    await expect(page.locator(`h1:has-text("${data.title}"), h2:has-text("${data.title}")`)).toBeVisible()
  })

  test('should navigate to sub-chapters from chapter', async ({ page }) => {
    const data = generateUniqueTestData().chapter

    await createChapter(page, data)

    // Click on chapter
    await page.click(`text=${data.title}`)

    // Look for sub-chapters section or navigation
    const hasSubChapters = await page.locator('text=/Sub-Chapters|Sub Chapters|Scenes/i').count() > 0
    expect(hasSubChapters).toBeTruthy()

    // Look for button to create sub-chapter or view sub-chapters
    const hasSubChapterAction = await page.locator('button:has-text("Sub-Chapter"), button:has-text("Scene"), button:has-text("Add Scene")').count() > 0
    expect(hasSubChapterAction).toBeTruthy()
  })

  test('should navigate back to book from chapter', async ({ page }) => {
    const data = generateUniqueTestData().chapter

    await createChapter(page, data)
    await page.click(`text=${data.title}`)

    // Look for back button or breadcrumb
    const backButton = page.locator('button:has-text("Back"), a:has-text("Back to Book"), [data-testid="back-button"]')

    if (await backButton.count() > 0) {
      await backButton.click()

      // Should return to book/chapters view
      await expect(page.locator('text=Book 1')).toBeVisible()
      await expect(page.locator(`text=${data.title}`)).toBeVisible()
    }
  })
})

test.describe('Chapter Validation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.primary.email, TEST_USERS.primary.password)

    // Create trilogy
    await page.goto('/dashboard')
    const trilogyData = testTrilogies.consciousness
    await createTrilogy(page, trilogyData)

    // Navigate to Book 1 chapters
    await page.click(`text=${trilogyData.title}`)
    await page.click('text=Book 1')
  })

  test.afterEach(async ({ page }) => {
    await page.goto('/dashboard')
    await cleanupTestData(page)
  })

  test('should require chapter title', async ({ page }) => {
    // Try to create without title
    await page.click('button:has-text("Create"), button:has-text("Add Chapter")')

    // Fill only plot notes
    await page.fill('textarea[name="chapter_plot"], textarea[id="plot"]', 'A chapter without a title')

    // Try to submit
    await page.click('button:has-text("Create"), button:has-text("Save")')

    // Should show validation error
    const hasError = await page.locator('text=/required|Required|must|Title/i').count() > 0
    expect(hasError).toBeTruthy()
  })

  test('should allow chapter without POV character', async ({ page }) => {
    // Create chapter without POV
    const data = {
      title: 'Chapter Without POV',
      chapter_plot: 'This chapter has no POV character assigned yet'
    }

    await createChapter(page, data)

    // Should successfully create
    await expect(page.locator(`text=${data.title}`)).toBeVisible()
  })

  test('should handle long chapter titles', async ({ page }) => {
    const longTitle = 'Chapter 1: The Very Long Title That Describes The Beginning Of The Journey Into The Unknown Reaches Of Quantum Consciousness'

    await createChapter(page, {
      title: longTitle,
      chapter_plot: 'Test plot'
    })

    // Should create successfully
    await expect(page.locator(`text=/The Very Long Title/i`)).toBeVisible()
  })

  test('should validate target word count is numeric', async ({ page }) => {
    await page.click('button:has-text("Create"), button:has-text("Add Chapter")')

    await page.fill('input[name="title"], input[id="title"]', 'Test Chapter')

    // Try to enter non-numeric word count
    const wordCountField = page.locator('input[name="target_word_count"], input[id="word-count"], input[type="number"]')

    if (await wordCountField.count() > 0) {
      await wordCountField.fill('not a number')

      // Should either reject input or show error
      const value = await wordCountField.inputValue()
      expect(value).not.toBe('not a number')
    }
  })
})
