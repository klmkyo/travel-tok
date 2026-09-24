import 'i18next'

import type { TRANSLATION_NAMESPACE } from '@/features/i18n/constants/messages'
import type en from '@/features/i18n/messages/en'

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: typeof TRANSLATION_NAMESPACE
    enableSelector: true
    resources: {
      [TRANSLATION_NAMESPACE]: typeof en
    }
  }
}
