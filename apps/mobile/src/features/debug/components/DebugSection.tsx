import type { ReactNode } from 'react'
import { View } from 'react-native'

import { ThemedText } from '@/common/components/themed-text/ThemedText'

export const DebugSection = ({ title, footer, children }: DebugSectionProps) => {
  return (
    <View className="gap-2">
      <ThemedText className="px-4 text-xs font-semibold tracking-widest text-base-600 uppercase dark:text-base-300">
        {title}
      </ThemedText>

      <View className="gap-5 rounded-3xl bg-container-50 px-5 py-4 border-continuous dark:bg-container-900">
        {children}
      </View>

      {footer && (
        <ThemedText className="px-4 text-xs leading-4 text-base-600 dark:text-base-300">
          {footer}
        </ThemedText>
      )}
    </View>
  )
}

type DebugSectionProps = {
  title: string
  footer?: ReactNode
  children: ReactNode
}
