import { valuesOf } from '@/common/helpers/object'

// Make sure to update app.config.ts too.
export enum ELocale {
  EN = 'en',
  PL = 'pl',
}

export const LOCALES = valuesOf(ELocale)

export const DEFAULT_LOCALE = ELocale.EN
