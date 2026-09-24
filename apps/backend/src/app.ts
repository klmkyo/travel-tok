import { Hono } from 'hono'

import type { AppDependencies } from './dependencies.js'
import { createHealthRoutes } from './health/health-routes.js'
import { createRequestLogger } from './middleware/request-logger.js'
import { createUserRoutes } from './user/user-routes.js'

// TODO do we even need all this createX bs? or can we just use the dependencies directly?
export const createApp = (dependencies: AppDependencies) =>
  new Hono()
    .use(createRequestLogger(dependencies.logger))
    .on(['POST', 'GET'], '/api/auth/*', c => dependencies.auth.handler(c.req.raw))
    .route('/', createHealthRoutes(dependencies))
    .route('/user', createUserRoutes(dependencies))

export type AppType = ReturnType<typeof createApp>
