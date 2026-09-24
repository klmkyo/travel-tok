# Store file templates

Placeholders are `<feature>` in kebab-case and `FeatureName` in PascalCase. `src/features/debug/store/` is a working example of all four files.

Imports are always absolute through `@/`, including between sibling files in the same folder, because Oxlint restricts relative imports in `apps/mobile`.

## `<feature>-types.ts`

Holds all three types. This file is the one to read to learn what a store holds and does.

```ts
import type { ELocale } from '@/features/i18n/constants/locales'

export type FeatureNameState = {
  someValue: string
  overrideLocale: ELocale | null
}

export type FeatureNameActions = {
  setSomeValue: (value: string) => void
  setIsLocaleOverrideEnabled: (enabled: boolean) => void
}

export type FeatureNameStore = FeatureNameState & FeatureNameActions
```

## `<feature>-state.ts`

Initial values only. Derive defaults from the outside world here, not in the component that reads them.

```ts
import type { FeatureNameState } from '@/features/<feature>/store/<feature>-types'

export const createFeatureNameState = (): FeatureNameState => ({
  someValue: 'default',
  overrideLocale: null,
})
```

## `<feature>-actions.ts`

`immer` lets actions mutate the draft directly.

```ts
import type { StateCreator } from 'zustand'

import type {
  FeatureNameActions,
  FeatureNameStore,
} from '@/features/<feature>/store/<feature>-types'

export const createFeatureNameActions: StateCreator<
  FeatureNameStore,
  [['zustand/immer', never]],
  [],
  FeatureNameActions
> = (set, get) => ({
  setSomeValue: value => {
    set(state => {
      state.someValue = value
    })
  },
  setIsLocaleOverrideEnabled: enabled => {
    set(state => {
      state.overrideLocale = enabled ? getSupportedDeviceLocale() : null
    })
  },
})
```

Read the current value with `get()` when an action needs it. Drop `get` from the parameter list when no action does; nothing requires it.

## `<feature>-store.ts`, persisted

The order of the middleware matters: `persist` wraps `immer`, so the actions still mutate drafts.

```ts
import { persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import { createStore } from 'zustand/vanilla'

import { ELocalStorageKey } from '@/common/storage/local-storage-key'
import { type PersistedState, type StatePersistenceMap } from '@/common/storage/state-persistence'
import { createZustandPersistMmkvStorage } from '@/common/storage/zustand-persist-mmkv-storage'
import { createFeatureNameActions } from '@/features/<feature>/store/<feature>-actions'
import { createFeatureNameState } from '@/features/<feature>/store/<feature>-state'
import type { FeatureNameState, FeatureNameStore } from '@/features/<feature>/store/<feature>-types'

const FEATURE_NAME_STATE_PERSISTENCE = {
  someValue: true,
  overrideLocale: true,
} satisfies StatePersistenceMap<FeatureNameState>

type PersistedFeatureNameState = PersistedState<
  FeatureNameState,
  typeof FEATURE_NAME_STATE_PERSISTENCE
>

export const createFeatureNameStore = () => {
  return createStore<FeatureNameStore>()(
    persist(
      immer((set, get, api) => ({
        ...createFeatureNameState(),
        ...createFeatureNameActions(set, get, api),
      })),
      {
        name: ELocalStorageKey.FEATURE_NAME_STORE,
        storage: createZustandPersistMmkvStorage<PersistedFeatureNameState>(),
        partialize: state =>
          ({
            someValue: state.someValue,
            overrideLocale: state.overrideLocale,
          }) satisfies PersistedFeatureNameState,
      },
    ),
  )
}

export const featureNameStore = createFeatureNameStore()
```

The persistence map and `partialize` list the same keys twice, and TypeScript keeps them honest: the map decides which keys `PersistedState` contains, so a key missing from `partialize` fails the `satisfies`, and a key missing from the map is a compile error on the map itself.

## `<feature>-store.ts`, nothing persisted

```ts
import { immer } from 'zustand/middleware/immer'
import { createStore } from 'zustand/vanilla'

import { createFeatureNameActions } from '@/features/<feature>/store/<feature>-actions'
import { createFeatureNameState } from '@/features/<feature>/store/<feature>-state'
import type { FeatureNameStore } from '@/features/<feature>/store/<feature>-types'

export const createFeatureNameStore = () => {
  return createStore<FeatureNameStore>()(
    immer((set, get, api) => ({
      ...createFeatureNameState(),
      ...createFeatureNameActions(set, get, api),
    })),
  )
}

export const featureNameStore = createFeatureNameStore()
```

## `hooks/useFeatureNameStore.ts`

```ts
import { useStore } from 'zustand'

import { featureNameStore } from '@/features/<feature>/store/<feature>-store'
import type { FeatureNameStore } from '@/features/<feature>/store/<feature>-types'

export const useFeatureNameStore = <T>(selector: (store: FeatureNameStore) => T): T => {
  return useStore(featureNameStore, selector)
}
```

Callers select one value at a time, so the component only re-renders for what it reads:

```ts
const someValue = useFeatureNameStore(state => state.someValue)
const setSomeValue = useFeatureNameStore(state => state.setSomeValue)
```

## `src/common/storage/local-storage-key.ts`

Add an entry for each persisted store. The string is the MMKV key, so changing one is a breaking change for stored data.

```ts
export enum ELocalStorageKey {
  DEBUG_STORE = 'debug-store',
  THEME_STORE = 'theme-store',
  FEATURE_NAME_STORE = 'feature-name-store',
}
```
