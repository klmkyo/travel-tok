// Repo-root oxfmt config. Applies to every file with no nearer config: the root tooling files,
// apps/backend, and anything else outside apps/mobile.
import { defineConfig } from 'oxfmt'

import base from './oxfmt.base.mts'

export default defineConfig({
  ...base,

  ignorePatterns: [
    'node_modules',
    'dist',
    '**/ios',
    '**/android',
    'pnpm-lock.yaml',
    'workbench',

    '**/drizzle',

    '.agents/skills/uniwind',
  ],
})
