import type { MiddlewareHandler } from 'hono'

import type { Logger } from '../logger.js'

export const createRequestLogger = (logger: Logger): MiddlewareHandler => {
  return async (c, next) => {
    const startedAt = performance.now()

    await next()

    logger.info(
      {
        method: c.req.method,
        path: c.req.path,
        status: c.res.status,
        durationMs: Math.round(performance.now() - startedAt),
      },
      'request',
    )
  }
}
