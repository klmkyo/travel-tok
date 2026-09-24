import { createMiddleware } from 'hono/factory'

import type { Auth } from '../auth/auth.js'

export type SessionEnv = {
  Variables: {
    session: Auth['$Infer']['Session'] | null
  }
}

type SessionDependencies = {
  auth: Auth
}

export const createSessionMiddleware = ({ auth }: SessionDependencies) =>
  createMiddleware<SessionEnv>(async (c, next) => {
    const session = await auth.api.getSession({
      headers: c.req.raw.headers,
    })

    c.set('session', session)

    await next()
  })
