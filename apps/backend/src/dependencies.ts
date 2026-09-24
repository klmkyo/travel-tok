import type { Auth } from './auth/auth.js'
import type { Database } from './db/db.js'
import type { Logger } from './logger.js'

export type AppDependencies = {
  logger: Logger
  db: Database
  auth: Auth
}
