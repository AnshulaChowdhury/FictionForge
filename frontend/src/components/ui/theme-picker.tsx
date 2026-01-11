/**
 * Theme picker component for switching between themes.
 * Compact minimalist design.
 */

import { useThemeStore, themes, type ThemeId } from '@/stores/themeStore'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { Palette, Check } from 'lucide-react'

export function ThemePicker() {
  const { theme, setTheme } = useThemeStore()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
          title="Change theme"
        >
          <Palette className="h-4 w-4" />
          <span className="sr-only">Change theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {themes.map((t) => (
          <DropdownMenuItem
            key={t.id}
            onClick={() => setTheme(t.id as ThemeId)}
            className="flex items-center gap-2 cursor-pointer text-sm"
          >
            <span className="text-sm">{t.icon}</span>
            <span className="flex-1">{t.name}</span>
            {theme === t.id && (
              <Check className="h-3.5 w-3.5 text-accent" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
