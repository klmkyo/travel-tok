import { Select } from '@/common/components/ui/select/Select'
import { valuesOf } from '@/common/helpers/object'
import { useSettingsStore } from '@/features/settings/hooks/useSettingsStore'
import { EColorSchemePreference } from '@/features/theme/constants/color-scheme'

const COLOR_SCHEME_OPTIONS = valuesOf(EColorSchemePreference)

const COLOR_SCHEME_LABELS = {
  [EColorSchemePreference.SYSTEM]: 'System',
  [EColorSchemePreference.LIGHT]: 'Light',
  [EColorSchemePreference.DARK]: 'Dark',
} satisfies Record<EColorSchemePreference, string>

export const ColorSchemeSelect = () => {
  const colorSchemePreference = useSettingsStore(state => state.colorSchemePreference)
  const setColorSchemePreference = useSettingsStore(state => state.setColorSchemePreference)

  return (
    <Select
      options={COLOR_SCHEME_OPTIONS}
      value={colorSchemePreference}
      onChange={setColorSchemePreference}
      getLabel={preference => COLOR_SCHEME_LABELS[preference]}
    />
  )
}
