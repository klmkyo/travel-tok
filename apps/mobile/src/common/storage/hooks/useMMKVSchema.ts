import { type SetStateAction, useCallback, useEffect, useMemo } from 'react'
import { useMMKVString } from 'react-native-mmkv'
import { z } from 'zod'

import { type ELocalStorageKey } from '@/common/storage/local-storage-key'

type UseMMKVSchemaOptions<T> = {
  key: ELocalStorageKey | (string & {})
  schema: z.ZodType<T, string>
  /**
   * Value used when the key is missing or the stored string fails decode.
   * Pass a function when the fallback should depend on the raw stored string (e.g. for migration).
   */
  fallback: T | ((stored: string | undefined) => T)
}

const getFallbackValue = <T>(
  stored: string | undefined,
  fallback: T | ((stored: string | undefined) => T),
): T => {
  if (typeof fallback === 'function') {
    return (fallback as (stored: string | undefined) => T)(stored)
  }

  return fallback
}

const resolveSchemaValue = <T>(
  stored: string | undefined,
  schema: z.ZodType<T, string>,
  fallback: T | ((stored: string | undefined) => T),
): T => {
  if (stored !== undefined) {
    const result = z.safeDecode(schema, stored)
    if (result.success) {
      return result.data
    }
  }

  return getFallbackValue(stored, fallback)
}

/**
 * Reads and writes a typed value in MMKV through a Zod schema.
 *
 * The schema's input type must be `string`, because that is what MMKV stores.
 * On read, `safeDecode` turns the string into `T`. On write, `encode` turns
 * `T` back into a string. If the key is missing or decode fails, you get
 * `fallback`. When a stored string is invalid, an effect replaces it with the
 * encoded fallback so the next read succeeds.
 *
 * Returns `[value, setValue]`. `setValue` accepts a next value or an updater
 * function, same as `useState`.
 *
 * @example Enum string
 * ```ts
 * const preferenceSchema = z.enum(['system', 'light', 'dark'])
 *
 * const [preference, setPreference] = useMMKVSchema({
 *   key: 'color-scheme',
 *   schema: preferenceSchema,
 *   fallback: 'system',
 * })
 *
 * setPreference('dark')
 * setPreference(current => (current === 'dark' ? 'light' : 'dark'))
 * ```
 *
 * @example JSON object with a codec
 * ```ts
 * const draftSchema = z.codec(z.string(), z.object({ title: z.string() }), {
 *   decode: json => JSON.parse(json),
 *   encode: value => JSON.stringify(value),
 * })
 *
 * const [draft, setDraft] = useMMKVSchema({
 *   key: 'compose-draft',
 *   schema: draftSchema,
 *   fallback: { title: '' },
 * })
 * ```
 *
 * @example Fallback from the raw stored string
 * ```ts
 * const [count, setCount] = useMMKVSchema({
 *   key: 'visit-count',
 *   schema: z.codec(z.string(), z.number(), {
 *     decode: raw => Number(raw),
 *     encode: value => String(value),
 *   }),
 *   // Old builds wrote "yes" / "no". Map those once, then the effect rewrites.
 *   fallback: stored => (stored === 'yes' ? 1 : 0),
 * })
 * ```
 */
export const useMMKVSchema = <T>({ key, schema, fallback }: UseMMKVSchemaOptions<T>) => {
  const [stored, setStored] = useMMKVString(key)

  const value = useMemo(
    () => resolveSchemaValue(stored, schema, fallback),
    [stored, schema, fallback],
  )

  useEffect(() => {
    if (stored === undefined) {
      return
    }

    if (z.safeDecode(schema, stored).success) {
      return
    }

    const resolved = getFallbackValue(stored, fallback)
    const encoded = z.safeEncode(schema, resolved)
    if (!encoded.success) {
      return
    }

    if (encoded.data !== stored) {
      setStored(encoded.data)
    }
  }, [stored, schema, fallback, setStored])

  const setValue = useCallback(
    (valueOrFunc: SetStateAction<T>) => {
      if (typeof valueOrFunc === 'function') {
        setStored(currentStored => {
          const current = resolveSchemaValue(currentStored, schema, fallback)
          const next = (valueOrFunc as (previous: T) => T)(current)
          return z.encode(schema, next)
        })
        return
      }

      setStored(z.encode(schema, valueOrFunc))
    },
    [setStored, schema, fallback],
  )

  return [value, setValue] as const
}
