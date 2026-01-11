/**
 * Chapter navigation (Level 3) - shows chapter info and sub-chapters list.
 */

import { useQuery } from '@tanstack/react-query'
import { getChapter } from '@/api/chapters'
import { getChapterSubChapters } from '@/api/subChapters'
import { getBook } from '@/api/trilogy'
import { BackButton } from './BackButton'
import { TrilogyTools } from './TrilogyTools'
import { ProgressIndicator } from './ProgressIndicator'
import { Check, Circle, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface ChapterNavProps {
  chapterId: string
  isCollapsed?: boolean
}

export function ChapterNav({ chapterId, isCollapsed = false }: ChapterNavProps) {
  const { data: chapter, isLoading: chapterLoading } = useQuery({
    queryKey: ['chapter', chapterId],
    queryFn: () => getChapter(chapterId),
    enabled: !!chapterId,
  })

  const { data: subChapters, isLoading: subChaptersLoading } = useQuery({
    queryKey: ['chapter', chapterId, 'sub-chapters'],
    queryFn: () => getChapterSubChapters(chapterId),
    enabled: !!chapterId,
  })

  // Fetch book to get trilogy_id
  const { data: book } = useQuery({
    queryKey: ['book', chapter?.book_id],
    queryFn: () => getBook(chapter!.book_id),
    enabled: !!chapter?.book_id,
  })

  const isLoading = chapterLoading || subChaptersLoading

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        <div className="h-4 bg-accent rounded animate-pulse" />
        <div className="h-4 bg-accent rounded animate-pulse w-3/4" />
      </div>
    )
  }

  if (!chapter) {
    return (
      <div className="p-4 text-sm text-destructive">
        Failed to load chapter
      </div>
    )
  }

  const bookId = chapter.book_id
  const trilogyId = book?.trilogy_id

  // Determine status icon for each sub-chapter
  const getStatusIcon = (subChapter: any) => {
    if (subChapter.word_count > 0) {
      return <Check className="w-3 h-3 text-success" />
    }
    // Check if generating (this would need WebSocket or job tracking)
    // For now, just show empty indicator
    return <Circle className="w-3 h-3 text-muted-foreground" />
  }

  return (
    <div className="space-y-3">
      {/* Back Button */}
      <BackButton
        label="Chapters"
        to={`/book/${bookId}/chapters`}
        isCollapsed={isCollapsed}
      />

      {/* Chapter Header - compact */}
      {!isCollapsed && (
        <div className="px-2.5 py-2 border-b border-border space-y-1.5">
          <h2 className="text-sm font-medium text-foreground truncate">
            {chapter.title}
          </h2>
          {chapter.target_word_count && (
            <ProgressIndicator
              current={chapter.current_word_count}
              target={chapter.target_word_count}
              showBar
            />
          )}
        </div>
      )}

      {/* Sub-Chapters Section */}
      <div className="space-y-0.5">
        {subChapters && subChapters.length > 0 ? (
          <>
            {subChapters
              .sort((a, b) => a.sub_chapter_number - b.sub_chapter_number)
              .map((subChapter) => (
                <div
                  key={subChapter.id}
                  className={cn(
                    'px-2.5 py-2 rounded transition-colors',
                    'hover:bg-muted',
                    isCollapsed && 'px-2 flex items-center justify-center'
                  )}
                  title={isCollapsed ? subChapter.title || `Sub-chapter ${subChapter.sub_chapter_number}` : undefined}
                >
                  {isCollapsed ? (
                    <div className="w-5 h-5 bg-muted text-muted-foreground rounded flex items-center justify-center text-xs font-medium">
                      {subChapter.sub_chapter_number}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="flex-shrink-0">
                        {getStatusIcon(subChapter)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-4 flex-shrink-0">
                            {subChapter.sub_chapter_number}.
                          </span>
                          <span className="text-sm text-foreground truncate">
                            {subChapter.title || `Sub-chapter ${subChapter.sub_chapter_number}`}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground pl-6">
                          {subChapter.word_count > 0 ? (
                            <span>{subChapter.word_count.toLocaleString()} words</span>
                          ) : (
                            <span className="opacity-60">No content</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
          </>
        ) : (
          !isCollapsed && (
            <div className="px-2.5 py-2 text-xs text-muted-foreground">
              No sub-chapters yet
            </div>
          )
        )}

        {/* Add Sub-Chapter Button */}
        {!isCollapsed && (
          <div className="pt-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-muted-foreground"
              onClick={() => {
                // Navigation handled in main page
              }}
            >
              <Plus className="w-3.5 h-3.5 mr-2" />
              Add Sub-Chapter
            </Button>
          </div>
        )}
      </div>

      {/* Divider before Trilogy Tools */}
      {!isCollapsed && trilogyId && <div className="border-t border-border mx-2" />}

      {/* Trilogy Tools - Quick Access */}
      {!isCollapsed && trilogyId && (
        <TrilogyTools trilogyId={trilogyId} isCollapsed={isCollapsed} />
      )}
    </div>
  )
}
