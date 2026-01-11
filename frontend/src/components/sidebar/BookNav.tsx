/**
 * Book navigation (Level 2) - shows book info and chapters list.
 */

import { useQuery } from '@tanstack/react-query'
import { getBook, getTrilogyBooks } from '@/api/trilogy'
import { getBookChapters } from '@/api/chapters'
import { BackButton } from './BackButton'
import { TrilogyTools } from './TrilogyTools'
import { ProgressIndicator } from './ProgressIndicator'
import { ChevronRight, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface BookNavProps {
  bookId: string
  isCollapsed?: boolean
}

export function BookNav({ bookId, isCollapsed = false }: BookNavProps) {
  const navigate = useNavigate()

  const { data: book, isLoading: bookLoading } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => getBook(bookId),
    enabled: !!bookId,
  })

  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['book', bookId, 'chapters'],
    queryFn: () => getBookChapters(bookId),
    enabled: !!bookId,
  })

  // Fetch all books from the trilogy to determine book position
  const { data: allBooks } = useQuery({
    queryKey: ['trilogy', book?.trilogy_id, 'books'],
    queryFn: () => getTrilogyBooks(book!.trilogy_id),
    enabled: !!book?.trilogy_id,
  })

  const isLoading = bookLoading || chaptersLoading
  const chapters = chaptersData?.chapters || []

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        <div className="h-4 bg-accent rounded animate-pulse" />
        <div className="h-4 bg-accent rounded animate-pulse w-3/4" />
      </div>
    )
  }

  if (!book) {
    return (
      <div className="p-4 text-sm text-destructive">
        Failed to load book
      </div>
    )
  }

  const trilogyId = book.trilogy_id
  const totalBooks = allBooks?.length || 3

  return (
    <div className="space-y-3">
      {/* Back Button */}
      <BackButton
        label="Books"
        to={`/trilogy/${trilogyId}`}
        isCollapsed={isCollapsed}
      />

      {/* Book Header - compact */}
      {!isCollapsed && (
        <div className="px-2.5 py-2 border-b border-border space-y-1.5">
          <h2 className="text-sm font-medium text-foreground truncate">
            {book.title}
          </h2>
          <ProgressIndicator
            current={book.current_word_count}
            target={book.target_word_count}
            showBar
          />
        </div>
      )}

      {/* Chapters Section */}
      <div className="space-y-0.5">
        {chapters.length > 0 ? (
          <>
            {chapters
              .sort((a, b) => a.chapter_number - b.chapter_number)
              .map((chapter) => (
                <button
                  key={chapter.id}
                  onClick={() => navigate(`/chapter/${chapter.id}/sub-chapters`)}
                  className={cn(
                    'w-full text-left px-2.5 py-2 rounded transition-colors',
                    'hover:bg-muted group',
                    isCollapsed && 'px-2 flex items-center justify-center'
                  )}
                  title={isCollapsed ? chapter.title : undefined}
                >
                  {isCollapsed ? (
                    <div className="w-5 h-5 bg-muted text-muted-foreground rounded flex items-center justify-center text-xs font-medium">
                      {chapter.chapter_number}
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="text-xs text-muted-foreground w-4 flex-shrink-0">
                            {chapter.chapter_number}.
                          </span>
                          <span className="text-sm text-foreground truncate">
                            {chapter.title}
                          </span>
                        </div>
                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </div>

                      {chapter.target_word_count && (
                        <div className="text-xs text-muted-foreground pl-6">
                          {chapter.current_word_count.toLocaleString()} / {chapter.target_word_count.toLocaleString()}
                        </div>
                      )}
                    </div>
                  )}
                </button>
              ))}
          </>
        ) : (
          !isCollapsed && (
            <div className="px-2.5 py-2 text-xs text-muted-foreground">
              No chapters yet
            </div>
          )
        )}

        {/* Add Chapter Button */}
        {!isCollapsed && (
          <div className="pt-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-muted-foreground"
              onClick={() => navigate(`/book/${bookId}/chapters`)}
            >
              <Plus className="w-3.5 h-3.5 mr-2" />
              Add Chapter
            </Button>
          </div>
        )}
      </div>

      {/* Divider before Trilogy Tools */}
      {!isCollapsed && <div className="border-t border-border mx-2" />}

      {/* Trilogy Tools - Quick Access */}
      {!isCollapsed && (
        <TrilogyTools trilogyId={trilogyId} isCollapsed={isCollapsed} />
      )}
    </div>
  )
}
