import { NativeTabs } from 'expo-router/unstable-native-tabs'
import { useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useUniwind } from 'uniwind'

import { useThemeColors } from '@/common/hooks/useThemeColors'
import { useDebugStore } from '@/features/debug/hooks/useDebugStore'
import { useI18n } from '@/features/i18n/hooks/useI18n'

const DEBUG_TAP_COUNT_TO_ENABLE = 7
const DEBUG_TAP_WINDOW_MS = 1_000

export const unstable_settings = {
  initialRouteName: 'index',
}

export default function TabsLayout() {
  const { locale } = useI18n()
  const { t } = useTranslation()

  const theme = useThemeColors()
  const { theme: colorScheme } = useUniwind()

  const debugEnabled = useDebugStore(state => state.debugEnabled)
  const handleHomeTabPress = useToggleDebugOnHomeTaps()

  const backgroundColor = colorScheme === 'dark' ? theme.container[950] : theme.container[100]
  const tintColor = colorScheme === 'dark' ? theme.primary[400] : theme.primary[600]

  return (
    <NativeTabs key={locale} tintColor={tintColor} backgroundColor={backgroundColor}>
      <NativeTabs.Trigger name="index" listeners={{ tabPress: handleHomeTabPress }}>
        <NativeTabs.Trigger.Label>{t($ => $.routes.home)}</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'house', selected: 'house.fill' }}
          md={{ default: 'home', selected: 'home' }}
        />
      </NativeTabs.Trigger>

      {debugEnabled && (
        <NativeTabs.Trigger name="debug">
          <NativeTabs.Trigger.Label>Debug</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon
            sf={{ default: 'switch.2', selected: 'switch.2' }}
            md={{ default: 'toggle_on', selected: 'toggle_on' }}
          />
        </NativeTabs.Trigger>
      )}
    </NativeTabs>
  )
}

const useToggleDebugOnHomeTaps = () => {
  const toggleDebugEnabled = useDebugStore(state => state.toggleDebugEnabled)
  const homeTapRef = useRef({ count: 0, lastTapAt: 0 })

  return useCallback(() => {
    const now = Date.now()
    const isWithinTapWindow = now - homeTapRef.current.lastTapAt <= DEBUG_TAP_WINDOW_MS
    const nextTapCount = isWithinTapWindow ? homeTapRef.current.count + 1 : 1

    homeTapRef.current = {
      count: nextTapCount,
      lastTapAt: now,
    }

    if (nextTapCount >= DEBUG_TAP_COUNT_TO_ENABLE) {
      homeTapRef.current = { count: 0, lastTapAt: 0 }
      toggleDebugEnabled()
    }
  }, [toggleDebugEnabled])
}
