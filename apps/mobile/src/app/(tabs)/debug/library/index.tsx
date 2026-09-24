import { Stack } from 'expo-router'

import { ComponentLibraryScreen } from '@/features/debug/library/ComponentLibraryScreen'

export default function ComponentLibraryIndexScreen() {
  return (
    <>
      <Stack.Screen
        options={{
          title: 'Component library',
        }}
      />
      <ComponentLibraryScreen />
    </>
  )
}
