import { DefaultTheme, ThemeProvider as ExpoThemeProvider } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { type ReactNode, useLayoutEffect, useMemo } from 'react'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Uniwind, useUniwind } from 'uniwind'

import { useThemeColors } from '@/common/hooks/useThemeColors'
import { useSettingsStore } from '@/features/settings/hooks/useSettingsStore'

export const ThemeProvider = ({ children }: ThemeProviderProps) => {
  const { theme } = useUniwind()
  const colors = useThemeColors()

  const colorSchemePreference = useSettingsStore(state => state.colorSchemePreference)

  const { top, bottom, left, right } = useSafeAreaInsets()

  useLayoutEffect(() => {
    Uniwind.setTheme(colorSchemePreference)
  }, [colorSchemePreference])

  useLayoutEffect(() => {
    Uniwind.updateInsets({ top, bottom, left, right })
  }, [top, bottom, left, right])

  const isDark = theme === 'dark'

  const navigationTheme: ReactNavigation.Theme = useMemo(
    () => ({
      colors: {
        primary: isDark ? colors.primary[400] : colors.primary[600],
        background: isDark ? colors.container[950] : colors.container[100],
        card: isDark ? colors.container[900] : colors.container[50],
        text: isDark ? colors.base[100] : colors.base[900],
        border: isDark ? colors.container[800] : colors.container[300],
        notification: isDark ? colors.primary[400] : colors.primary[600],
      },
      dark: isDark,
      fonts: DefaultTheme.fonts,
    }),
    [colors, isDark],
  )

  return (
    <ExpoThemeProvider value={navigationTheme}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      {children}
    </ExpoThemeProvider>
  )
}

type ThemeProviderProps = {
  children: ReactNode
}
