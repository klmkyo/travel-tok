import { persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import { createStore } from 'zustand/vanilla'

import { ELocalStorageKey } from '@/common/storage/local-storage-key'
import { type PersistedState, type StatePersistenceMap } from '@/common/storage/state-persistence'
import { createZustandPersistMmkvStorage } from '@/common/storage/zustand-persist-mmkv-storage'
import { createDebugActions } from '@/features/debug/store/debug-actions'
import { createDebugState } from '@/features/debug/store/debug-state'
import type { DebugState, DebugStore } from '@/features/debug/store/debug-types'

const DEBUG_STATE_PERSISTENCE = {
  debugEnabled: true,
  overrideLocale: true,
} satisfies StatePersistenceMap<DebugState>

type PersistedDebugState = PersistedState<DebugState, typeof DEBUG_STATE_PERSISTENCE>

export const createDebugStore = () => {
  return createStore<DebugStore>()(
    persist(
      immer((set, get, api) => ({
        ...createDebugState(),
        ...createDebugActions(set, get, api),
      })),
      {
        name: ELocalStorageKey.DEBUG_STORE,
        storage: createZustandPersistMmkvStorage<PersistedDebugState>(),
        partialize: state =>
          ({
            debugEnabled: state.debugEnabled,
            overrideLocale: state.overrideLocale,
          }) satisfies PersistedDebugState,
      },
    ),
  )
}

export const debugStore = createDebugStore()
