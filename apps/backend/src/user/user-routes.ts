import { Hono } from 'hono'

import type { AppDependencies } from '../dependencies.js'
import { createSessionMiddleware } from '../middleware/session.js'

export const createUserRoutes = ({ auth }: AppDependencies) =>
  new Hono().use(createSessionMiddleware({ auth })).get('/me', c => {
    const session = c.var.session

    if (!session) {
      return c.json({ error: 'unauthorized' }, 401)
    }

    return c.json({ user: session.user })
  })
