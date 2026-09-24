import { type PropsWithChildren, useCallback, useLayoutEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { useDebugStore } from '@/features/debug/hooks/useDebugStore'
import { type ELocale, LOCALES } from '@/features/i18n/constants/locales'
import { I18nContext } from '@/features/i18n/contexts/I18nContext'
import { getSupportedDeviceLocale, isValidLocale } from '@/features/i18n/helpers'

export const I18nContextProvider = ({ children }: PropsWithChildren) => {
  const { i18n: i18nInstance } = useTranslation()
  const overrideLocale = useDebugStore(state => state.overrideLocale)

  const locale = getI18nInstanceLocale(i18nInstance.language)

  const setLocale = useCallback(
    async (nextLocale: ELocale) => {
      await i18nInstance.changeLanguage(nextLocale)
    },
    [i18nInstance],
  )

  useLayoutEffect(() => {
    const nextLocale = overrideLocale ?? getSupportedDeviceLocale()

    if (getI18nInstanceLocale(i18nInstance.language) !== nextLocale) {
      void i18nInstance.changeLanguage(nextLocale)
    }
  }, [i18nInstance, overrideLocale])

  return (
    <I18nContext.Provider
      value={{
        locale,
        locales: LOCALES,
        setLocale,
      }}
    >
      {children}
    </I18nContext.Provider>
  )
}

const getI18nInstanceLocale = (language: string): ELocale => {
  const normalized = language.split('-')[0] ?? language

  if (!isValidLocale(normalized)) {
    throw new Error(`Invalid i18n instance language: ${language}`)
  }

  return normalized
}
