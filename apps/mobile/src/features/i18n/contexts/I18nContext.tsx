import { createContext } from 'react'

import type { ELocale, LOCALES } from '@/features/i18n/constants/locales'

export type I18nContextValue = {
  locale: ELocale
  locales: typeof LOCALES
  setLocale: (locale: ELocale) => Promise<void>
}

export const I18nContext = createContext<I18nContextValue | null>(null)
