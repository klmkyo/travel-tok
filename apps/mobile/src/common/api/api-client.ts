import type { AppType } from 'backend'
import { hc } from 'hono/client'

import { environment } from '@/environment'
import { authClient } from '@/features/auth/auth-client'

export const api = hc<AppType>(environment.EXPO_PUBLIC_API_URL, {
  init: { credentials: 'omit' },
  headers: async (): Promise<Record<string, string>> => {
    const cookie = await authClient.getCookie()

    return cookie === '' ? {} : { Cookie: cookie }
  },
})
