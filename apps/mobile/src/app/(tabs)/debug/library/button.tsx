import { Stack } from 'expo-router'

import { ButtonGallery } from '@/features/debug/library/galleries/ButtonGallery'

export default function ButtonGalleryScreen() {
  return (
    <>
      <Stack.Screen
        options={{
          title: 'Button',
        }}
      />
      <ButtonGallery />
    </>
  )
}
