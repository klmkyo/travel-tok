import type { EColorSchemePreference } from '@/features/theme/constants/color-scheme'

export type SettingsState = {
  colorSchemePreference: EColorSchemePreference
}

export type SettingsActions = {
  setColorSchemePreference: (preference: EColorSchemePreference) => void
}

export type SettingsStore = SettingsState & SettingsActions
