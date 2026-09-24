import { SymbolView, type SymbolViewProps } from 'expo-symbols'
import type { ComponentProps } from 'react'
import type { ColorValue } from 'react-native'
import Animated from 'react-native-reanimated'
import { withUniwind } from 'uniwind'

type SymbolNameByPlatform = Exclude<SymbolViewProps['name'], string>

export type PlatformSymbolName = {
  ios: NonNullable<SymbolNameByPlatform['ios']> | null
  android: NonNullable<SymbolNameByPlatform['android']> | null
}

const StyledSymbolView = withUniwind(SymbolView)

const FALLBACK_SYMBOL_NAME = {
  ios: 'questionmark.app.dashed',
  android: 'question_mark',
  web: 'question_mark',
} as const satisfies SymbolViewProps['name']

export const IconSymbol = ({
  name,
  size,
  color,
  colorClassName,
  style,
  weight = 'regular',
  className,
  ...props
}: IconSymbolProps) => {
  return (
    <StyledSymbolView
      name={
        {
          ios: name.ios ?? FALLBACK_SYMBOL_NAME.ios,
          android: name.android ?? FALLBACK_SYMBOL_NAME.android,
          web: name.android ?? FALLBACK_SYMBOL_NAME.web,
        } as const satisfies SymbolViewProps['name']
      }
      resizeMode="scaleAspectFit"
      size={size}
      weight={weight}
      // `exactOptionalPropertyTypes` rejects forwarding an explicitly undefined value into an
      // optional prop, and neither `expo-symbols` nor `withUniwind` types its optional props as
      // `X | undefined`. Spread each of those only when the caller set one.
      {...(color === undefined ? {} : { tintColor: color })}
      {...(colorClassName === undefined ? {} : { tintColorClassName: colorClassName })}
      {...(className === undefined ? {} : { className })}
      style={[
        {
          width: size,
          height: size,
        },
        style,
      ]}
      {...props}
    />
  )
}

export const AnimatedIconSymbol = Animated.createAnimatedComponent(IconSymbol)

export interface IconSymbolProps {
  name: PlatformSymbolName
  size: number
  color?: ColorValue
  colorClassName?: string
  style?: ComponentProps<typeof SymbolView>['style']
  weight?: SymbolViewProps['weight']
  className?: string
}
