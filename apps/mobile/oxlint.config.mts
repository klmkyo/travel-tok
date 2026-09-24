import { defineConfig } from 'oxlint'
import native from 'oxlint-config-universe/native'

import rootConfig from '../../oxlint.config.mts'

const assetRequireAllow = [
  '\\.(aac|aiff|avif|bmp|caf|db|gif|heic|html|jpeg|jpg|json|m4a|m4v|mov|mp3|mp4|mpeg|mpg|otf|pdf|png|psd|svg|ttf|wav|webm|webp|xml|yaml|yml|zip)$',
]

export default defineConfig({
  extends: [native, rootConfig],

  plugins: ['import', 'node', 'react', 'typescript', 'unicorn'],
  jsPlugins: ['eslint-plugin-expo'],

  settings: {
    react: {
      version: '19.3.0',
    },
  },

  env: {
    es2024: true,
  },
  globals: {
    console: 'readonly',
    exports: 'readonly',
    global: 'readonly',
    module: 'readonly',
    require: 'readonly',
    __DEV__: 'readonly',
    Atomics: 'readonly',
    ErrorUtils: 'readonly',
    FormData: 'readonly',
    SharedArrayBuffer: 'readonly',
    XMLHttpRequest: 'readonly',
    alert: 'readonly',
    cancelAnimationFrame: 'readonly',
    cancelIdleCallback: 'readonly',
    clearImmediate: 'readonly',
    clearInterval: 'readonly',
    clearTimeout: 'readonly',
    fetch: 'readonly',
    navigator: 'readonly',
    process: 'readonly',
    requestAnimationFrame: 'readonly',
    requestIdleCallback: 'readonly',
    setImmediate: 'readonly',
    setInterval: 'readonly',
    setTimeout: 'readonly',
    window: 'readonly',
  },

  ignorePatterns: [
    'node_modules/**',
    '.expo/**',
    'dist/**',
    'build/**',
    'coverage/**',
    'ios/**',
    'android/**',
    'assets/**',
    'src/uniwind-types.d.ts',
    'babel.config.js',
  ],

  rules: {
    'react/self-closing-comp': 'error',
    'react/jsx-curly-brace-presence': ['error', { propElementValues: 'always' }],
    'react/exhaustive-deps': 'warn',

    'expo/use-dom-exports': 'error',
    'expo/no-env-var-destructuring': 'error',
    'expo/no-dynamic-env-var': 'error',

    // React Compiler is enabled in app.config.ts.
    'react/static-components': 'error',
    'react/use-memo': 'error',
    'react/preserve-manual-memoization': 'error',
    'react/incompatible-library': 'warn',
    'react/immutability': 'error',
    'react/globals': 'error',
    'react/refs': 'error',
    'react/set-state-in-effect': 'error',
    'react/error-boundaries': 'error',
    'react/purity': 'error',
    'react/set-state-in-render': 'error',
    'react/unsupported-syntax': 'warn',

    // Assets are required by path at build time, which the rule cannot see through.
    'typescript/no-require-imports': [
      'error',
      {
        allow: assetRequireAllow,
      },
    ],

    'no-restricted-imports': [
      'error',
      {
        patterns: [
          {
            group: ['../**', './**'],
            message: 'Import through the @/ alias instead of a relative path.',
          },
          {
            group: ['@expo/ui', '@expo/ui/**'],
            message:
              'Use the themed wrappers in @/common/components/ui/ instead of importing Expo UI directly.',
          },
        ],
        paths: [
          {
            name: 'react-native',
            importNames: ['Text'],
            message: 'Use ThemedText from @/common/components/themed-text/ThemedText instead.',
          },
          {
            name: 'react-native',
            importNames: ['SafeAreaView'],
            message:
              'Use SafeAreaView from @/common/components/safe-area-view/SafeAreaView instead.',
          },
          {
            name: 'react-native',
            importNames: ['useColorScheme'],
            message: 'Use useUniwind() from uniwind for the resolved light/dark theme.',
          },
          {
            name: 'react-native',
            importNames: ['Button'],
            message: 'Use Button from @/common/components/ui/button/Button instead.',
          },
          {
            name: 'react-native',
            importNames: ['Switch'],
            message: 'Use Switch from @/common/components/ui/switch/Switch instead.',
          },
          {
            name: 'react-native-safe-area-context',
            importNames: ['SafeAreaView'],
            message:
              'Use SafeAreaView from @/common/components/safe-area-view/SafeAreaView instead.',
          },
          {
            name: 'expo-blur',
            importNames: ['BlurView'],
            message:
              'Use BlurView from @/common/components/blur-view/BlurView instead (Uniwind `withUniwind` wrapper).',
          },
          {
            name: 'expo-image',
            importNames: ['Image'],
            message:
              'Use Image from @/common/components/image/Image instead (Uniwind `withUniwind` wrapper).',
          },
          {
            name: 'expo-linear-gradient',
            importNames: ['LinearGradient'],
            message:
              'Use LinearGradient from @/common/components/linear-gradient/LinearGradient instead (Uniwind `withUniwind` wrapper).',
          },
        ],
      },
    ],
  },

  overrides: [
    {
      files: ['oxlint.config.mts', 'oxfmt.config.mts'],
      rules: {
        'no-restricted-imports': 'off',
      },
    },
  ],
})
