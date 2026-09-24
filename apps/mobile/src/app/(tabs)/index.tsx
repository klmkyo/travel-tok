import { useTranslation } from 'react-i18next'
import { View } from 'react-native'

import { ThemedText } from '@/common/components/themed-text/ThemedText'

export default function HomeScreen() {
  const { t } = useTranslation()

  return (
    <View className="flex-1 items-center justify-center gap-2 p-8">
      <ThemedText className="text-2xl font-semibold">{t($ => $.home.greeting)}</ThemedText>
    </View>
  )
}
