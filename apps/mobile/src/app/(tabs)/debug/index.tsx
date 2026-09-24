import { Redirect, Stack } from 'expo-router'

import { DebugPage } from '@/features/debug/DebugPage'
import { useDebugStore } from '@/features/debug/hooks/useDebugStore'

export default function DebugScreen() {
  const debugEnabled = useDebugStore(state => state.debugEnabled)

  if (!debugEnabled) {
    return <Redirect href="/" />
  }

  return (
    <>
      <Stack.Screen
        options={{
          headerLargeTitleEnabled: true,
          title: 'Debug',
        }}
      />

      <DebugPage />
    </>
  )
}
