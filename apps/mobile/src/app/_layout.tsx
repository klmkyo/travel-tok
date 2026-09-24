import '@/global.css'

import { Stack } from 'expo-router'

import { useDefaultStackScreenOptions } from '@/common/hooks/useDefaultStackScreenOptions'
import { ProvidersProvider } from '@/common/providers/ProvidersProvider'

export default function RootLayout() {
  return (
    <ProvidersProvider>
      <RootStack />
    </ProvidersProvider>
  )
}

function RootStack() {
  const screenOptions = useDefaultStackScreenOptions()

  return (
    <Stack screenOptions={screenOptions}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
    </Stack>
  )
}
