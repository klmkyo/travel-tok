import type { ReactNode } from 'react'

import { GestureHandlerProvider } from '@/common/providers/GestureHandlerProvider'
import { GlobalEventsProvider } from '@/common/providers/GlobalEventsProvider'
import { I18nProvider } from '@/features/i18n/providers/I18nProvider'
import { QueryProvider } from '@/features/query/providers/QueryProvider'
import { ThemeProvider } from '@/features/theme/providers/ThemeProvider'

const providers = [
  GestureHandlerProvider,
  ThemeProvider,
  QueryProvider,
  I18nProvider,
  GlobalEventsProvider,
]

export const ProvidersProvider = ({ children }: ProvidersProviderProps) => {
  return providers.reduceRight((children, Provider, index) => {
    return <Provider key={index}>{children}</Provider>
  }, children)
}

type ProvidersProviderProps = {
  children: ReactNode
}
