import { ScrollView } from 'react-native'

import { BUTTON_VARIANTS, Button } from '@/common/components/ui/button/Button'
import { DebugSection } from '@/features/debug/components/DebugSection'

export const ButtonGallery = () => {
  return (
    <ScrollView contentContainerClassName="gap-6 px-5 py-6">
      <DebugSection title="Variants">
        {BUTTON_VARIANTS.map(variant => (
          <Button key={variant} variant={variant} label={variant} />
        ))}
      </DebugSection>

      <DebugSection title="States">
        {BUTTON_VARIANTS.map(variant => (
          <Button key={variant} variant={variant} label={variant} disabled />
        ))}
      </DebugSection>
    </ScrollView>
  )
}
