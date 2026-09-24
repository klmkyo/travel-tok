import { createInstance } from 'i18next'
import { initReactI18next } from 'react-i18next'

import { isExpoDev } from '@/common/helpers/is-expo-dev'
import { DEFAULT_LOCALE } from '@/features/i18n/constants/locales'
import { resources, TRANSLATION_NAMESPACE } from '@/features/i18n/constants/messages'
import { getSupportedDeviceLocale } from '@/features/i18n/helpers'

export const i18n = createInstance()

void i18n.use(initReactI18next).init({
  resources,
  lng: getSupportedDeviceLocale(),
  fallbackLng: DEFAULT_LOCALE,
  defaultNS: TRANSLATION_NAMESPACE,
  enableSelector: true,
  debug: isExpoDev(),
  interpolation: {
    escapeValue: false,
  },
})
