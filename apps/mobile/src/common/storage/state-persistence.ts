/**
 * Exhaustive map of which state keys should be persisted.
 *
 * Every key of `State` must appear with a boolean. `true` means the value is
 * written to storage; `false` means it is not. Adding a state property without
 * classifying it is a TypeScript error.
 *
 * @example
 * ```ts
 * type SettingsState = {
 *   colorSchemePreference: 'system' | 'light' | 'dark'
 *   sessionToken: string | null
 * }
 *
 * const SETTINGS_STATE_PERSISTENCE = {
 *   colorSchemePreference: true,
 *   sessionToken: false,
 * } satisfies StatePersistenceMap<SettingsState>
 * ```
 */
export type StatePersistenceMap<State extends object> = {
  [Key in keyof State]: boolean
}

type PersistedKeys<PersistenceMap extends object> = {
  [Key in keyof PersistenceMap]: PersistenceMap[Key] extends true ? Key : never
}[keyof PersistenceMap]

/**
 * The subset of `State` whose keys are marked `true` in `PersistenceMap`.
 *
 * Use this for the MMKV storage generic and for the `partialize` return type so
 * both stay aligned with the persistence map.
 *
 * @example
 * ```ts
 * const SETTINGS_STATE_PERSISTENCE = {
 *   colorSchemePreference: true,
 *   sessionToken: false,
 * } satisfies StatePersistenceMap<SettingsState>
 *
 * // { colorSchemePreference: 'system' | 'light' | 'dark' }
 * type PersistedSettingsState = PersistedState<
 *   SettingsState,
 *   typeof SETTINGS_STATE_PERSISTENCE
 * >
 *
 * partialize: state =>
 *   ({
 *     colorSchemePreference: state.colorSchemePreference,
 *   }) satisfies PersistedSettingsState
 * ```
 */
export type PersistedState<
  State extends object,
  PersistenceMap extends StatePersistenceMap<State>,
> = Pick<State, Extract<PersistedKeys<PersistenceMap>, keyof State>>
