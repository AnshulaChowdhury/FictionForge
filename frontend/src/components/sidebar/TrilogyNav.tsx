/**
 * Trilogy navigation (Level 1) - shows trilogy info, tools, and books.
 */

import { useQuery } from '@tanstack/react-query'
import { getTrilogy, getTrilogyBooks } from '@/api/trilogy'
import { BackButton } from './BackButton'
import { TrilogyTools } from './TrilogyTools'
import { ProgressIndicator } from './ProgressIndicator'
import { ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface TrilogyNavProps {
  trilogyId: string
  isCollapsed?: boolean
}

export function TrilogyNav({ trilogyId, isCollapsed = false }: TrilogyNavProps) {
  const navigate = useNavigate()

  const { data: trilogy, isLoading: trilogyLoading } = useQuery({
    queryKey: ['trilogy', trilogyId],
    queryFn: () => getTrilogy(trilogyId),
    enabled: !!trilogyId,
  })

  const { data: books, isLoading: booksLoading } = useQuery({
    queryKey: ['trilogy', trilogyId, 'books'],
    queryFn: () => getTrilogyBooks(trilogyId),
    enabled: !!trilogyId,
  })

  const isLoading = trilogyLoading || booksLoading

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        <div className="h-4 bg-accent rounded animate-pulse" />
        <div className="h-4 bg-accent rounded animate-pulse w-3/4" />
      </div>
    )
  }

  if (!trilogy) {
    return (
      <div className="p-4 text-sm text-destructive">
        Failed to load trilogy
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Back Button */}
      <BackButton label="Dashboard" to="/dashboard" isCollapsed={isCollapsed} />

      {/* Trilogy Header - compact */}
      {!isCollapsed && (
        <div className="px-2.5 py-2 border-b border-border">
          <h2 className="text-sm font-medium text-foreground truncate">
            {trilogy.title}
          </h2>
        </div>
      )}

      {/* Trilogy Tools */}
      <TrilogyTools trilogyId={trilogyId} isCollapsed={isCollapsed} />

      {/* Divider */}
      {!isCollapsed && <div className="border-t border-border mx-2" />}

      {/* Books Section */}
      <div className="space-y-0.5">
        {books && books.length > 0 ? (
          <>
            {books
              .sort((a, b) => a.book_number - b.book_number)
              .map((book) => (
                <button
                  key={book.id}
                  onClick={() => navigate(`/book/${book.id}/chapters`)}
                  className={cn(
                    'w-full text-left px-2.5 py-2 rounded transition-colors',
                    'hover:bg-muted group',
                    isCollapsed && 'px-2 flex items-center justify-center'
                  )}
                  title={isCollapsed ? book.title : undefined}
                >
                  {isCollapsed ? (
                    <div className="w-5 h-5 bg-muted text-muted-foreground rounded flex items-center justify-center text-xs font-medium">
                      {book.book_number}
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="text-xs text-muted-foreground w-4 flex-shrink-0">
                            {book.book_number}.
                          </span>
                          <span className="text-sm text-foreground truncate">
                            {book.title}
                          </span>
                        </div>
                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </div>

                      <ProgressIndicator
                        current={book.current_word_count}
                        target={book.target_word_count}
                        showBar
                      />
                    </div>
                  )}
                </button>
              ))}
          </>
        ) : (
          !isCollapsed && (
            <div className="px-2.5 py-2 text-xs text-muted-foreground">
              No books yet
            </div>
          )
        )}
      </div>
    </div>
  )
}
