import { processColor } from 'react-native'
import { useCSSVariable } from 'uniwind'

import { entriesOf, fromEntriesOf, valuesOf } from '@/common/helpers/object'
import {
  THEME_COLOR_VARIABLES,
  type ThemeColorScale,
  type ThemeColorShade,
} from '@/features/theme/constants/theme-colors'

export type ThemeColors = Record<ThemeColorScale, Record<ThemeColorShade, string>>

const CSS_COLOR_VARIABLES: string[] = valuesOf(THEME_COLOR_VARIABLES).flatMap(scale =>
  valuesOf(scale),
)

export const useThemeColors = (): ThemeColors => {
  const cssColorValues = useCSSVariable(CSS_COLOR_VARIABLES)

  // Uniwind resolves the variables by position, so index them by name once and look up per shade.
  const cssColorValueByVariable = fromEntriesOf(
    CSS_COLOR_VARIABLES.map((variable, index) => [variable, cssColorValues[index]] as const),
  )

  return fromEntriesOf(
    entriesOf(THEME_COLOR_VARIABLES).map(
      ([scale, shades]) =>
        [
          scale,
          fromEntriesOf(
            entriesOf(shades).map(([shade, variable]) => {
              const cssColorValue = cssColorValueByVariable[variable]

              if (typeof cssColorValue !== 'string' || processColor(cssColorValue) === null) {
                throw new Error(
                  `CSS variable ${variable} did not resolve to a color value. Received: ${String(cssColorValue)}`,
                )
              }

              return [shade, cssColorValue] as const
            }),
          ),
        ] as const,
    ),
  )
}
