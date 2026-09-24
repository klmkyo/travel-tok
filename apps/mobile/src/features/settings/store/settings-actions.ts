import type { StateCreator } from 'zustand'

import type { SettingsActions, SettingsStore } from '@/features/settings/store/settings-types'

export const createSettingsActions: StateCreator<
  SettingsStore,
  [['zustand/immer', never]],
  [],
  SettingsActions
> = set => ({
  setColorSchemePreference: preference => {
    set(state => {
      state.colorSchemePreference = preference
    })
  },
})
