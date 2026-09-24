import { drizzleAdapter } from '@better-auth/drizzle-adapter/relations-v2'
import { betterAuth } from 'better-auth'

import type { Database } from '../db/db.js'
import { schema } from '../db/schema.js'

type AuthDependencies = {
  db: Database
}

export const createAuth = ({ db }: AuthDependencies) =>
  betterAuth({
    database: drizzleAdapter(db, {
      provider: 'pg',
      schema,
    }),
    advanced: {
      database: {
        // let postgres pick the UUID itself
        generateId: 'uuid',
      },
    },
    emailAndPassword: {
      enabled: true,
    },
  })

export type Auth = ReturnType<typeof createAuth>
