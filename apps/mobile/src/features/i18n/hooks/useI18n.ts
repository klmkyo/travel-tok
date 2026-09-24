import { useI18nContext } from '@/features/i18n/hooks/useI18nContext'

export const useI18n = () => {
  const { locale, setLocale, locales } = useI18nContext()

  return { locale, setLocale, locales }
}
