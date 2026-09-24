type ObjectEntry<BaseType> = [keyof BaseType, BaseType[keyof BaseType]]
type ObjectEntries<BaseType> = ObjectEntry<BaseType>[]

export type Entries<BaseType> = BaseType extends object ? ObjectEntries<BaseType> : never

export function keysOf<T extends object>(obj: T): (keyof T)[] {
  return Object.keys(obj) as (keyof T)[]
}

export function valuesOf<T extends object>(obj: T): T[keyof T][] {
  return Object.values(obj) as T[keyof T][]
}

export function entriesOf<T extends object>(obj: T) {
  return Object.entries(obj) as Entries<T>
}

export const fromEntriesOf = <const T extends readonly (readonly [PropertyKey, unknown])[]>(
  entries: T,
): { [K in T[number] as K[0]]: K[1] } => {
  return Object.fromEntries(entries) as { [K in T[number] as K[0]]: K[1] }
}

type Falsy = false | 0 | 0n | '' | null | undefined

export type NoFalsy<T> = T extends Falsy
  ? never
  : T extends readonly (infer Item)[]
    ? NoFalsy<Item>[]
    : T extends object
      ? { [Key in keyof T]: NoFalsy<T[Key]> }
      : T

export function assertNoFalsyValues<T>(
  value: T,
  path: string[] = [],
): asserts value is T & NoFalsy<T> {
  if (typeof value === 'object' && value !== null) {
    for (const [key, nestedValue] of entriesOf(value)) {
      assertNoFalsyValues(nestedValue, [...path, String(key)])
    }
    return
  }

  if (!value) {
    const pathLabel = path.length > 0 ? path.join('.') : 'value'
    throw new Error(`Expected a truthy value at ${pathLabel}`)
  }
}
