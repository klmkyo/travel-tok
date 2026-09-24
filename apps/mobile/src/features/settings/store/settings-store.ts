import { persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import { createStore } from 'zustand/vanilla'

import { ELocalStorageKey } from '@/common/storage/local-storage-key'
import { type PersistedState, type StatePersistenceMap } from '@/common/storage/state-persistence'
import { createZustandPersistMmkvStorage } from '@/common/storage/zustand-persist-mmkv-storage'
import { createSettingsActions } from '@/features/settings/store/settings-actions'
import { createSettingsState } from '@/features/settings/store/settings-state'
import type { SettingsState, SettingsStore } from '@/features/settings/store/settings-types'

const SETTINGS_STATE_PERSISTENCE = {
  colorSchemePreference: true,
} satisfies StatePersistenceMap<SettingsState>

type PersistedSettingsState = PersistedState<SettingsState, typeof SETTINGS_STATE_PERSISTENCE>

export const createSettingsStore = () => {
  return createStore<SettingsStore>()(
    persist(
      immer((set, get, api) => ({
        ...createSettingsState(),
        ...createSettingsActions(set, get, api),
      })),
      {
        name: ELocalStorageKey.SETTINGS_STORE,
        storage: createZustandPersistMmkvStorage<PersistedSettingsState>(),
        partialize: state =>
          ({
            colorSchemePreference: state.colorSchemePreference,
          }) satisfies PersistedSettingsState,
      },
    ),
  )
}

export const settingsStore = createSettingsStore()
