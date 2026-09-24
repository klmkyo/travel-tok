import { serve } from '@hono/node-server'
import { migrate } from 'drizzle-orm/postgres-js/migrator'

import { createApp } from './app.js'
import { createAuth } from './auth/auth.js'
import { createDb } from './db/db.js'
import type { AppDependencies } from './dependencies.js'
import { environment } from './environment.js'
import { createLogger } from './logger.js'

const makeDependencies = (): AppDependencies => {
  const db = createDb(environment.DATABASE_URL)

  return {
    logger: createLogger({
      level: environment.LOG_LEVEL,
      pretty: environment.NODE_ENV === 'development',
    }),
    db,
    auth: createAuth({ db }),
  }
}

const dependencies: AppDependencies = makeDependencies()

await migrate(dependencies.db, { migrationsFolder: './drizzle' })

serve(
  {
    fetch: createApp(dependencies).fetch,
    port: environment.PORT,
  },
  info => {
    dependencies.logger.info({ port: info.port }, 'server listening')
  },
)
