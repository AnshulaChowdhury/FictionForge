/**
 * Zen Mode - Distraction-free writing experience.
 * Full-screen, minimal UI, just you and your words.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'

interface ZenModeProps {
  isOpen: boolean
  onClose: () => void
  content: string
  onContentChange: (content: string) => void
  placeholder?: string
}

export function ZenMode({
  isOpen,
  onClose,
  content,
  onContentChange,
  placeholder = 'Begin writing...',
}: ZenModeProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [wordCount, setWordCount] = useState(0)

  // Calculate word count
  useEffect(() => {
    const words = content.trim().split(/\s+/).filter((w) => w.length > 0)
    setWordCount(words.length)
  }, [content])

  // Handle escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    },
    [onClose]
  )

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
      // Focus the textarea
      setTimeout(() => {
        textareaRef.current?.focus()
      }, 100)
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  return createPortal(
    <div className="zen-mode">
      {/* Exit hint */}
      <button onClick={onClose} className="zen-mode-exit">
        ESC to exit
      </button>

      {/* Writing area */}
      <div className="zen-mode-content">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => onContentChange(e.target.value)}
          placeholder={placeholder}
          className="zen-mode-textarea"
          spellCheck="true"
        />
      </div>

      {/* Word count */}
      <div className="zen-mode-word-count">
        {wordCount.toLocaleString()} {wordCount === 1 ? 'word' : 'words'}
      </div>
    </div>,
    document.body
  )
}
