import { Pressable } from 'react-native'

import { IconSymbol, type PlatformSymbolName } from '@/common/components/icon-symbol/IconSymbol'
import { useSettingsStore } from '@/features/settings/hooks/useSettingsStore'
import { EColorSchemePreference } from '@/features/theme/constants/color-scheme'

const THEME_SYMBOLS = {
  [EColorSchemePreference.SYSTEM]: {
    ios: 'circle.lefthalf.filled',
    android: 'contrast',
  },
  [EColorSchemePreference.LIGHT]: {
    ios: 'sun.max',
    android: 'light_mode',
  },
  [EColorSchemePreference.DARK]: {
    ios: 'moon',
    android: 'dark_mode',
  },
} as const satisfies Record<EColorSchemePreference, PlatformSymbolName>

const NEXT_PREFERENCE = {
  [EColorSchemePreference.SYSTEM]: EColorSchemePreference.LIGHT,
  [EColorSchemePreference.LIGHT]: EColorSchemePreference.DARK,
  [EColorSchemePreference.DARK]: EColorSchemePreference.SYSTEM,
} satisfies Record<EColorSchemePreference, EColorSchemePreference>

export const ColorSchemeIconButton = () => {
  const colorSchemePreference = useSettingsStore(state => state.colorSchemePreference)
  const setColorSchemePreference = useSettingsStore(state => state.setColorSchemePreference)

  const handlePress = () => {
    setColorSchemePreference(NEXT_PREFERENCE[colorSchemePreference])
  }

  return (
    // TODO this is bad, cause you can hit the headerRight without touching the pressable
    <Pressable accessibilityRole="button" accessibilityLabel="Color scheme" onPress={handlePress}>
      <IconSymbol name={THEME_SYMBOLS[colorSchemePreference]} size={22} />
    </Pressable>
  )
}
