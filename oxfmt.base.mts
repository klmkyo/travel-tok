import { defineConfig } from 'oxfmt'

export default defineConfig({
  printWidth: 100,
  semi: false,
  singleQuote: true,
  trailingComma: 'all',
  arrowParens: 'avoid',
  sortPackageJson: true,
  sortImports: {
    ignoreCase: false,
    internalPattern: ['@/', '#/'],
    groups: [
      'side_effect',
      ['type-builtin', 'value-builtin', 'type-external', 'value-external'],
      ['type-internal', 'value-internal', 'type-subpath', 'value-subpath'],
      ['type-parent', 'value-parent', 'type-sibling', 'value-sibling', 'type-index', 'value-index'],
      'unknown',
    ],
  },
})
