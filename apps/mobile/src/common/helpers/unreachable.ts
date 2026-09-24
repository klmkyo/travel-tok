export const assertUnreachable = (value: never): never => {
  throw new Error(`Reached an unreachable value: ${JSON.stringify(value)}`)
}

export const unreachable = <T extends never>(value: T): T => {
  return value
}
