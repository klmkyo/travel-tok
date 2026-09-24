// oxlint-disable-next-line no-restricted-imports -- wrapper re-exports the restricted host
import { Switch as ExpoUiSwitch, type SwitchProps } from '@expo/ui'

import { ExpoUiHost } from '@/common/components/ui/expo-ui-host/ExpoUiHost'

export const Switch = (props: SwitchProps) => {
  return (
    <ExpoUiHost matchContents>
      <ExpoUiSwitch {...props} />
    </ExpoUiHost>
  )
}
