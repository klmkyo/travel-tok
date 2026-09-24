import { entriesOf, fromEntriesOf } from '@/common/helpers/object'
import { ELocale } from '@/features/i18n/constants/locales'
import en from '@/features/i18n/messages/en'
import pl from '@/features/i18n/messages/pl'

export const TRANSLATION_NAMESPACE = 'translation' as const

type LocalizedMessages<T> = {
  [K in keyof T]: T[K] extends string ? string : LocalizedMessages<T[K]>
}

export const messages = {
  [ELocale.EN]: en,
  [ELocale.PL]: pl,
} as const satisfies Record<ELocale, LocalizedMessages<typeof en>>

export const resources = fromEntriesOf(
  entriesOf(messages).map(([locale, message]) => [locale, { [TRANSLATION_NAMESPACE]: message }]),
)
