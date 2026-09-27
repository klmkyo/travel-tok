import { cn } from 'cn'
import type { ComponentProps } from 'react'
// oxlint-disable-next-line no-restricted-imports -- wrapper re-exports the restricted host
import { Switch as RNSwitch } from 'react-native'

export const Switch = ({
  thumbColorClassName,
  trackColorOnClassName,
  trackColorOffClassName,
  ios_backgroundColorClassName,
  ...props
}: SwitchProps) => {
  return (
    <RNSwitch
      {...props}
      thumbColorClassName={cn('accent-base-50', thumbColorClassName)}
      trackColorOnClassName={cn(
        'accent-primary-700 dark:accent-primary-400',
        trackColorOnClassName,
      )}
      trackColorOffClassName={cn(
        'accent-container-300 dark:accent-container-700',
        trackColorOffClassName,
      )}
      ios_backgroundColorClassName={cn(
        'accent-container-300 dark:accent-container-700',
        ios_backgroundColorClassName,
      )}
    />
  )
}

type SwitchProps = ComponentProps<typeof RNSwitch>
