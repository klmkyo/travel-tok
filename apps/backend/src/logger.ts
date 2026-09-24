import pino from 'pino'
import type { Logger } from 'pino'

type LoggerConfig = {
  level: string
  pretty: boolean
}

export const createLogger = ({ level, pretty }: LoggerConfig): Logger => {
  return pino({
    level,
    ...(pretty ? { transport: { target: 'pino-pretty' } } : {}),
  })
}

export type { Logger }
