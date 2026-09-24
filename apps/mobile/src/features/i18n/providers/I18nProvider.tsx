import type { PropsWithChildren } from 'react'
import { I18nextProvider } from 'react-i18next'

import { i18n } from '@/features/i18n/i18n'
import { I18nContextProvider } from '@/features/i18n/providers/I18nContextProvider'

export const I18nProvider = ({ children }: PropsWithChildren) => {
  return (
    <I18nextProvider i18n={i18n}>
      <I18nContextProvider>{children}</I18nContextProvider>
    </I18nextProvider>
  )
}
