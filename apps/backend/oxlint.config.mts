import { defineConfig } from 'oxlint'

import rootConfig from '../../oxlint.config.mts'

export default defineConfig({
  extends: [rootConfig],

  plugins: ['import', 'node', 'typescript', 'unicorn'],

  env: {
    node: true,
    es2024: true,
  },

  ignorePatterns: ['node_modules/**', 'dist/**'],
})
