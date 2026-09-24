import { useStore } from 'zustand'

import { settingsStore } from '@/features/settings/store/settings-store'
import type { SettingsStore } from '@/features/settings/store/settings-types'

export const useSettingsStore = <T>(selector: (store: SettingsStore) => T): T => {
  return useStore(settingsStore, selector)
}
