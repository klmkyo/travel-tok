import { defineConfig } from 'oxfmt'

import base from '../../oxfmt.base.mts'

export default defineConfig({
  ...base,

  sortTailwindcss: {
    stylesheet: './src/global.css',

    // Keep in sync with `tailwindCSS.classFunctions` in the root .vscode/settings.json.
    functions: ['cn', 'clsx', 'useResolveClassNames'],

    attributes: [
      'class',
      'className',
      'headerClassName',
      'contentContainerClassName',
      'columnWrapperClassName',
      'endFillColorClassName',
      'imageClassName',
      'tintColorClassName',
      'ios_backgroundColorClassName',
      'thumbColorClassName',
      'trackColorOnClassName',
      'trackColorOffClassName',
      'selectionColorClassName',
      'cursorColorClassName',
      'underlineColorAndroidClassName',
      'placeholderTextColorClassName',
      'selectionHandleColorClassName',
      'colorsClassName',
      'progressBackgroundColorClassName',
      'titleColorClassName',
      'underlayColorClassName',
      'colorClassName',
      'drawerBackgroundColorClassName',
      'statusBarBackgroundColorClassName',
      'backdropColorClassName',
      'backgroundColorClassName',
      'ListFooterComponentClassName',
      'ListHeaderComponentClassName',
    ],
  },

  // The root config's ignorePatterns never apply here (nearest config wins, nothing merges),
  // and these patterns are rooted at apps/mobile and cannot reach outside it, so this list
  // stands on its own.
  ignorePatterns: [
    'node_modules',
    '.expo',
    'dist',
    'build',
    'coverage',
    'pnpm-lock.yaml',
    'ios',
    'android',
    'src/uniwind-types.d.ts',
  ],
})
