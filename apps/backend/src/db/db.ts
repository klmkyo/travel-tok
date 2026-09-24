import { drizzle } from 'drizzle-orm/postgres-js'

import { relations } from './schema.js'

export const createDb = (databaseUrl: string) => drizzle(databaseUrl, { relations })

export type Database = ReturnType<typeof createDb>
