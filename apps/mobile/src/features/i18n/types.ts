import type { useTranslation } from 'react-i18next'

export type TranslateFn = ReturnType<typeof useTranslation>['t']
