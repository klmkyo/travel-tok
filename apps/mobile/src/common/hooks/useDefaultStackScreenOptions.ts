import { type NativeStackNavigationOptions } from 'expo-router'
import { useResolveClassNames } from 'uniwind'

export const useDefaultStackScreenOptions = (): NativeStackNavigationOptions => {
  const { accentColor } = useResolveClassNames('accent-base-900 dark:accent-base-100')

  if (accentColor === undefined) {
    throw new Error('Failed to resolve header chrome color')
  }

  return {
    headerTransparent: true,
    headerBackButtonDisplayMode: 'minimal',

    // System back chevron ignores headerTintColor on iOS 26+:
    // https://github.com/react-navigation/react-navigation/issues/12932
    // Workaround uses unstable_headerLeftItems. Might be a bad idea, as this
    // does not have the hold to go back etc.
    // Actually not using workaround because the color is a good fit anyways lol
    headerTintColor: accentColor,
    // unstable_headerLeftItems: ({ tintColor, canGoBack }) => {
    //   if (!canGoBack) {
    //     return []
    //   }

    //   return [
    //     {
    //       type: 'button',
    //       label: t($ => $.common.action.go_back),
    //       icon: {
    //         type: 'sfSymbol',
    //         name: 'chevron.backward',
    //       },
    //       ...(tintColor === undefined ? {} : { tintColor }),
    //       onPress: () => {
    //         router.back()
    //       },
    //     },
    //   ]
    // },

    scrollEdgeEffects: {
      top: 'soft',
    },
  }
}
