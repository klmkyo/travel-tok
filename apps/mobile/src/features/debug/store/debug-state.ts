import { EAppVariant } from '@/common/constants/app-variant'
import { environment } from '@/environment'
import type { DebugState } from '@/features/debug/store/debug-types'

export const createDebugState = (): DebugState => ({
  debugEnabled: environment.EXPO_PUBLIC_APP_VARIANT === EAppVariant.DEVELOPMENT,
  overrideLocale: null,
})
