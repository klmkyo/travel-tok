import { createEnv } from '@t3-oss/env-core'
import { z } from 'zod'

import { EAppVariant } from '@/common/constants/app-variant'

export const environment = createEnv({
  clientPrefix: 'EXPO_PUBLIC_',
  client: {
    EXPO_PUBLIC_APP_VARIANT: z.enum(EAppVariant).default(EAppVariant.DEVELOPMENT),
    EXPO_PUBLIC_API_URL: z.url().default('http://localhost:3000'),
  },
  server: {},
  runtimeEnvStrict: {
    EXPO_PUBLIC_APP_VARIANT: process.env.EXPO_PUBLIC_APP_VARIANT,
    EXPO_PUBLIC_API_URL: process.env.EXPO_PUBLIC_API_URL,
  },
  emptyStringAsUndefined: true,
})
