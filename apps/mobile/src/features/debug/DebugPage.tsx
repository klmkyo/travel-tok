import { Alert, ScrollView, View } from 'react-native'

import { ThemedText } from '@/common/components/themed-text/ThemedText'
import { Button } from '@/common/components/ui/button/Button'
import { Select } from '@/common/components/ui/select/Select'
import { Switch } from '@/common/components/ui/switch/Switch'
import { ColorSchemeSelect } from '@/features/debug/components/ColorSchemeSelect'
import { DebugSection } from '@/features/debug/components/DebugSection'
import { useDebugStore } from '@/features/debug/hooks/useDebugStore'
import { useResetApp } from '@/features/debug/hooks/useResetApp'
import { LibraryLinkRow } from '@/features/debug/library/LibraryLinkRow'
import { ELocale } from '@/features/i18n/constants/locales'
import { getSupportedDeviceLocale } from '@/features/i18n/helpers'
import { useI18n } from '@/features/i18n/hooks/useI18n'

const ROW_LABEL_CLASSES = 'flex-1 text-base font-medium tracking-wide'

const LOCALE_LABELS = {
  [ELocale.EN]: 'English',
  [ELocale.PL]: 'Polski',
} satisfies Record<ELocale, string>

export const DebugPage = () => {
  const { locale, locales } = useI18n()

  const debugEnabled = useDebugStore(state => state.debugEnabled)
  const toggleDebugEnabled = useDebugStore(state => state.toggleDebugEnabled)

  const overrideLocale = useDebugStore(state => state.overrideLocale)
  const setOverrideLocale = useDebugStore(state => state.setOverrideLocale)

  const resetApp = useResetApp()

  const handleResetApp = () => {
    Alert.alert('Reset app?', 'This removes all local data and restarts the app.', [
      {
        text: 'Cancel',
        style: 'cancel',
      },
      {
        text: 'Reset',
        style: 'destructive',
        onPress: resetApp,
      },
    ])
  }

  return (
    <ScrollView contentContainerClassName="gap-6 px-5 py-6">
      <DebugSection title="General">
        <View className="flex-row items-center justify-between gap-4">
          <ThemedText className={ROW_LABEL_CLASSES}>Debug mode</ThemedText>
          <Switch value={debugEnabled} onValueChange={toggleDebugEnabled} />
        </View>
      </DebugSection>

      <DebugSection title="Appearance">
        <View className="flex-row items-center justify-between gap-4">
          <ThemedText className={ROW_LABEL_CLASSES}>Color scheme</ThemedText>
          <ColorSchemeSelect />
        </View>
      </DebugSection>

      <DebugSection title="Language" footer={`Resolved language: ${LOCALE_LABELS[locale]}`}>
        <View className="flex-row items-center justify-between gap-4">
          <ThemedText className={ROW_LABEL_CLASSES}>Override language</ThemedText>
          <Switch
            value={overrideLocale !== null}
            onValueChange={enabled => {
              setOverrideLocale(enabled ? getSupportedDeviceLocale() : null)
            }}
          />
        </View>

        {overrideLocale && (
          <View className="flex-row items-center justify-between gap-4">
            <ThemedText className={ROW_LABEL_CLASSES}>Language</ThemedText>
            <Select
              options={locales}
              value={overrideLocale}
              onChange={setOverrideLocale}
              getLabel={option => LOCALE_LABELS[option]}
            />
          </View>
        )}
      </DebugSection>

      <DebugSection title="Components">
        <LibraryLinkRow href="/debug/library" label="Component library" />
      </DebugSection>

      <View className="gap-2">
        <Button variant="destructive" label="Reset app" onPress={handleResetApp} />
        <ThemedText className="px-4 text-xs leading-4 text-base-600 dark:text-base-300">
          This removes all local data and restarts the app.
        </ThemedText>
      </View>
    </ScrollView>
  )
}
