import type { SettingsState } from '@/features/settings/store/settings-types'
import { EColorSchemePreference } from '@/features/theme/constants/color-scheme'

export const createSettingsState = (): SettingsState => ({
  colorSchemePreference: EColorSchemePreference.SYSTEM,
})
