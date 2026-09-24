---
name: zustand-store
description: Creates or changes Zustand stores in apps/mobile, covering the four-file store layout, the useXStore hook, and the exhaustive MMKV persistence map. Use when adding a store, adding state or actions to one, or deciding whether a state property persists.
---

# Zustand stores

A store is split across four small files so that state, actions, and the persistence decision each have one home and one place to change.

The persistence map is the part worth being careful about. It is exhaustive by construction: adding a state property and forgetting to classify it is a TypeScript error, not a silently unpersisted field.

## Instructions

1. Take the feature name from the request. If it is not stated, ask for it before writing anything.
2. Create `src/features/<feature>/store/` and write four files, all kebab-case: `<feature>-types.ts`, `<feature>-state.ts`, `<feature>-actions.ts`, and `<feature>-store.ts`. Use the templates in [references/store-files.md](references/store-files.md).
3. Create `src/features/<feature>/hooks/use<Feature>Store.ts`. Components read the store only through this hook, never from the store object directly.
4. Decide the persistence of each state property, then write the map. If anything persists, add the key to `ELocalStorageKey` in `src/common/storage/local-storage-key.ts`.
5. Run `pnpm check` in `apps/mobile`. The work is done when it passes with no new errors.

## The persistence map

- Every Zustand store must explicitly classify every property in its state type with a boolean: `true` means persistent and `false` means non-persistent.
- Define the classification with `satisfies StatePersistenceMap<StoreState>` from `@/common/storage/state-persistence`. The mapped type is intentionally exhaustive, so adding a state property without classifying it must produce a TypeScript error.
- Derive the persisted state with `PersistedState` and use that type for both `createZustandPersistMmkvStorage` and the store's `partialize` result.
- Keep actions out of the persistence map; classify only the state properties.

Classify by asking whether the value has to outlive the process. A user preference or a debug override does; data that is refetched on launch, or that is derived from something already persisted, does not.

## Files that do not persist

Some stores hold nothing that outlives the process. Leave out `persist`, the storage, the `StatePersistenceMap`, and the `ELocalStorageKey` entry, and call `immer(...)` directly inside `createStore`. Keep the four-file split and the `use<Feature>Store` hook either way, so a store that later gains persisted state changes in one file.
