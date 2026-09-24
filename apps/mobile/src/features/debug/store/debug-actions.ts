import type { StateCreator } from 'zustand'

import type { DebugActions, DebugStore } from '@/features/debug/store/debug-types'

export const createDebugActions: StateCreator<
  DebugStore,
  [['zustand/immer', never]],
  [],
  DebugActions
> = set => ({
  toggleDebugEnabled: () => {
    set(state => {
      state.debugEnabled = !state.debugEnabled
    })
  },
  setOverrideLocale: locale => {
    set(state => {
      state.overrideLocale = locale
    })
  },
})
