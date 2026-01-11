/**
 * Sparkle effect component for celebration moments.
 * Wraps content and triggers sparkles on demand.
 */

import { useState, useCallback } from 'react'

interface SparkleEffectProps {
  children: React.ReactNode
  className?: string
}

export function SparkleEffect({ children, className = '' }: SparkleEffectProps) {
  const [isSparklingLocal, setIsSparklingLocal] = useState(false)

  return (
    <div className={`sparkle-container ${className}`}>
      {children}
      {isSparklingLocal && (
        <>
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
        </>
      )}
    </div>
  )
}

/**
 * Hook to trigger sparkle animations
 */
export function useSparkle() {
  const [isSparklingMap, setIsSparklingMap] = useState<Record<string, boolean>>({})

  const triggerSparkle = useCallback((id: string, duration = 800) => {
    setIsSparklingMap((prev) => ({ ...prev, [id]: true }))
    setTimeout(() => {
      setIsSparklingMap((prev) => ({ ...prev, [id]: false }))
    }, duration)
  }, [])

  const isSparklingFor = useCallback(
    (id: string) => isSparklingMap[id] || false,
    [isSparklingMap]
  )

  return { triggerSparkle, isSparklingFor }
}

interface SparkleWrapperProps {
  id: string
  isSparklingFor: (id: string) => boolean
  children: React.ReactNode
  className?: string
}

export function SparkleWrapper({
  id,
  isSparklingFor,
  children,
  className = '',
}: SparkleWrapperProps) {
  const isSparkling = isSparklingFor(id)

  return (
    <div className={`sparkle-container ${className}`}>
      {children}
      {isSparkling && (
        <>
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
          <span className="sparkle" />
        </>
      )}
    </div>
  )
}

/**
 * Celebration component - shows a brief celebration animation
 */
interface CelebrationProps {
  show: boolean
  onComplete?: () => void
  children: React.ReactNode
}

export function Celebration({ show, onComplete, children }: CelebrationProps) {
  const [isAnimating, setIsAnimating] = useState(false)

  if (show && !isAnimating) {
    setIsAnimating(true)
    setTimeout(() => {
      setIsAnimating(false)
      onComplete?.()
    }, 600)
  }

  return (
    <div className={isAnimating ? 'animate-celebrate' : ''}>
      {children}
    </div>
  )
}
