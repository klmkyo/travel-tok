import * as Localization from 'expo-localization'

import { DEFAULT_LOCALE, type ELocale, LOCALES } from '@/features/i18n/constants/locales'

export const isValidLocale = (locale: string): locale is ELocale => {
  return LOCALES.includes(locale as ELocale)
}

export const getSupportedDeviceLocale = (): ELocale => {
  for (const { languageCode } of Localization.getLocales()) {
    if (languageCode !== null && isValidLocale(languageCode)) {
      return languageCode
    }
  }

  return DEFAULT_LOCALE
}
