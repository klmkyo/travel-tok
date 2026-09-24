export enum EColorSchemePreference {
  SYSTEM = 'system',
  LIGHT = 'light',
  DARK = 'dark',
}

export type ColorScheme = EColorSchemePreference.LIGHT | EColorSchemePreference.DARK
