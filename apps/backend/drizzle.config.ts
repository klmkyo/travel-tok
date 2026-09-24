import { defineConfig } from 'drizzle-kit'

import { environment } from './src/environment.js'

export default defineConfig({
  out: './drizzle',
  schema: './src/db/schema.ts',
  dialect: 'postgresql',
  dbCredentials: {
    url: environment.DATABASE_URL,
  },
})
