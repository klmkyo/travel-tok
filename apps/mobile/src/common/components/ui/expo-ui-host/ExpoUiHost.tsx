// oxlint-disable-next-line no-restricted-imports -- wrapper re-exports the restricted host
import { Host } from '@expo/ui'
import type { ComponentProps } from 'react'
import { useUniwind } from 'uniwind'

import { useThemeColors } from '@/common/hooks/useThemeColors'

// TODO revisit this if its even needed.

/**
 * Wraps Expo UI controls so they follow the app theme. Defaults `colorScheme` and `seedColor`
 * from the app palette; pass Host props to override. Callers that need content sizing must
 * pass `matchContents` themselves — Expo reads that prop only on mount.
 */
export const ExpoUiHost = ({ children, ...props }: ExpoUiHostProps) => {
  const { theme } = useUniwind()
  const colors = useThemeColors()

  // iOS uses the seed as a SwiftUI tint and Android derives a Material 3 palette from it, so a
  // mid-tone brand shade lands closest to our palette on both platforms.
  const seedColor = theme === 'dark' ? colors.primary[400] : colors.primary[600]

  return (
    <Host colorScheme={theme} seedColor={seedColor} {...props}>
      {children}
    </Host>
  )
}

type ExpoUiHostProps = ComponentProps<typeof Host>
