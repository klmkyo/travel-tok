import { expoClient } from '@better-auth/expo/client'
import { createAuthClient } from 'better-auth/react'
import * as SecureStore from 'expo-secure-store'

import { environment } from '@/environment'

export const authClient = createAuthClient({
  baseURL: environment.EXPO_PUBLIC_API_URL,
  plugins: [
    expoClient({
      scheme: 'traveltok',
      storagePrefix: 'traveltok',
      storage: SecureStore,
    }),
  ],
})
