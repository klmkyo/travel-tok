import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from 'cn'
import type { ComponentProps } from 'react'
import { Pressable, type GestureResponderEvent, type LayoutChangeEvent } from 'react-native'
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated'

import { ThemedText } from '@/common/components/themed-text/ThemedText'

export const BUTTON_VARIANTS = [
  'default',
  'destructive',
  'outline',
  'secondary',
  'ghost',
  'link',
] as const

export type ButtonVariant = (typeof BUTTON_VARIANTS)[number]

const buttonVariants = cva(
  'items-center justify-center rounded-xl border-continuous px-4 py-3 active:opacity-80 disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary-700 dark:bg-primary-400',
        destructive: 'bg-red-800 dark:bg-red-400',
        outline: 'border border-container-300 dark:border-container-700',
        secondary: 'bg-container-200 dark:bg-container-800',
        ghost: 'bg-transparent',
        link: 'px-0 py-0',
      } satisfies Record<ButtonVariant, string>,
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

// React Native text does not inherit color, so the label palette is a second map.
const buttonLabelVariants = cva('font-semibold', {
  variants: {
    variant: {
      default: 'text-base-50 dark:text-base-950',
      destructive: 'text-base-50 dark:text-base-950',
      outline: 'text-base-900 dark:text-base-100',
      secondary: 'text-base-900 dark:text-base-100',
      ghost: 'text-base-900 dark:text-base-100',
      link: 'text-primary-700 dark:text-primary-300 underline',
    } satisfies Record<ButtonVariant, string>,
  },
  defaultVariants: {
    variant: 'default',
  },
})

const PRESS_SHRINK_PX = 6
const PRESS_IN_DURATION_MS = 90
const PRESS_RELEASE_SPRING = { damping: 16, stiffness: 320 }

const AnimatedPressable = Animated.createAnimatedComponent(Pressable)

export const Button = ({
  label,
  variant,
  disabled = false,
  className,
  style,
  onLayout,
  onPressIn,
  onPressOut,
  ...props
}: ButtonProps) => {
  const buttonWidthSv = useSharedValue(0)
  const pressProgressSv = useSharedValue(0)

  const pressScaleStyle = useAnimatedStyle(() => {
    const width = buttonWidthSv.get()
    const shrinkRatio = width > 0 ? PRESS_SHRINK_PX / width : 0

    return {
      transform: [{ scale: 1 - shrinkRatio * pressProgressSv.get() }],
    }
  })

  const handleLayout = (event: LayoutChangeEvent) => {
    buttonWidthSv.set(event.nativeEvent.layout.width)
    onLayout?.(event)
  }

  const handlePressIn = (event: GestureResponderEvent) => {
    pressProgressSv.set(withTiming(1, { duration: PRESS_IN_DURATION_MS }))
    onPressIn?.(event)
  }

  const handlePressOut = (event: GestureResponderEvent) => {
    pressProgressSv.set(withSpring(0, PRESS_RELEASE_SPRING))
    onPressOut?.(event)
  }

  return (
    <AnimatedPressable
      {...props}
      className={cn(buttonVariants({ variant, className }))}
      style={[pressScaleStyle, style]}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      onLayout={handleLayout}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
    >
      <ThemedText className={buttonLabelVariants({ variant })}>{label}</ThemedText>
    </AnimatedPressable>
  )
}

type ButtonProps = Omit<ComponentProps<typeof Pressable>, 'children' | 'disabled'> &
  VariantProps<typeof buttonVariants> & {
    label: string
    disabled?: boolean
  }
