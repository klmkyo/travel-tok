import { useStore } from 'zustand'

import { debugStore } from '@/features/debug/store/debug-store'
import type { DebugStore } from '@/features/debug/store/debug-types'

export const useDebugStore = <T>(selector: (store: DebugStore) => T): T => {
  return useStore(debugStore, selector)
}
