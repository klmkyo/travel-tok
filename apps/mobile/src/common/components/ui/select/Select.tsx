// oxlint-disable-next-line no-restricted-imports -- wrapper re-exports the restricted host
import { Picker, type PickerProps } from '@expo/ui'

import { ExpoUiHost } from '@/common/components/ui/expo-ui-host/ExpoUiHost'

export const Select = <Option extends string>({
  options,
  value,
  onChange,
  getLabel,
  ...props
}: SelectProps<Option>) => {
  return (
    <ExpoUiHost matchContents>
      <Picker selectedValue={value} onValueChange={onChange} {...props}>
        {options.map(option => (
          <Picker.Item key={option} label={getLabel(option)} value={option} />
        ))}
      </Picker>
    </ExpoUiHost>
  )
}

type SelectProps<Option extends string> = Omit<
  PickerProps<Option>,
  'children' | 'onValueChange' | 'selectedValue'
> & {
  options: readonly Option[]
  value: Option
  onChange: (option: Option) => void
  getLabel: (option: Option) => string
}
