import { Hono } from 'hono'

import type { AppDependencies } from '../dependencies.js'

export const createHealthRoutes = ({ logger }: AppDependencies) =>
  new Hono()
    .get('/', c => {
      logger.info({ currentTime: new Date().toISOString() }, 'hello requested')
      return c.text('Hello Hono!')
    })
    .get('/health', c => {
      return c.json({ status: 'ok' })
    })
