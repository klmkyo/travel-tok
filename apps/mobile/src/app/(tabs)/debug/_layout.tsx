import { Stack } from 'expo-router'

import { useDefaultStackScreenOptions } from '@/common/hooks/useDefaultStackScreenOptions'
import { ColorSchemeIconButton } from '@/features/debug/components/ColorSchemeIconButton'

export const unstable_settings = {
  initialRouteName: 'index',
}

export default function DebugLayout() {
  const screenOptions = useDefaultStackScreenOptions()

  return (
    <Stack
      screenOptions={{
        ...screenOptions,
        headerRight: () => <ColorSchemeIconButton />,
      }}
    >
      <Stack.Screen name="index" options={{ headerRight: () => null }} />
    </Stack>
  )
}
