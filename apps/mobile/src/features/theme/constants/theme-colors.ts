// Keep in sync with the `@theme static` block in `src/global.css`.
export const THEME_COLOR_VARIABLES = {
  primary: {
    50: '--color-primary-50',
    100: '--color-primary-100',
    200: '--color-primary-200',
    300: '--color-primary-300',
    400: '--color-primary-400',
    500: '--color-primary-500',
    600: '--color-primary-600',
    700: '--color-primary-700',
    800: '--color-primary-800',
    900: '--color-primary-900',
    950: '--color-primary-950',
  },
  container: {
    50: '--color-container-50',
    100: '--color-container-100',
    200: '--color-container-200',
    300: '--color-container-300',
    400: '--color-container-400',
    500: '--color-container-500',
    600: '--color-container-600',
    700: '--color-container-700',
    800: '--color-container-800',
    900: '--color-container-900',
    950: '--color-container-950',
  },
  base: {
    50: '--color-base-50',
    100: '--color-base-100',
    200: '--color-base-200',
    300: '--color-base-300',
    400: '--color-base-400',
    500: '--color-base-500',
    600: '--color-base-600',
    700: '--color-base-700',
    800: '--color-base-800',
    900: '--color-base-900',
    950: '--color-base-950',
  },
} as const

export type ThemeColorScale = keyof typeof THEME_COLOR_VARIABLES
export type ThemeColorShade = keyof (typeof THEME_COLOR_VARIABLES)[ThemeColorScale]
