import { useContext } from 'react'

import { I18nContext } from '@/features/i18n/contexts/I18nContext'

export const useI18nContext = () => {
  const context = useContext(I18nContext)

  if (!context) {
    throw new Error('useI18nContext must be used within I18nContextProvider')
  }

  return context
}
