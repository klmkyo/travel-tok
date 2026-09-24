import type { ELocale } from '@/features/i18n/constants/locales'

export type DebugState = {
  debugEnabled: boolean
  overrideLocale: ELocale | null
}

export type DebugActions = {
  toggleDebugEnabled: () => void
  setOverrideLocale: (locale: ELocale | null) => void
}

export type DebugStore = DebugState & DebugActions
