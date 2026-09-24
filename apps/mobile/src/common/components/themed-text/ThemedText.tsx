import { cn } from 'cn'
import type { ComponentProps } from 'react'
// oxlint-disable-next-line no-restricted-imports -- wrapper re-exports the restricted host
import { Text } from 'react-native'

type ThemedTextProps = ComponentProps<typeof Text>

export const ThemedText = ({ className, ...props }: ThemedTextProps) => {
  return <Text className={cn('text-base-900 dark:text-base-100', className)} {...props} />
}
