import { ScrollView } from 'react-native'

import { DebugSection } from '@/features/debug/components/DebugSection'
import { LibraryLinkRow } from '@/features/debug/library/LibraryLinkRow'

const COMPONENT_LIBRARY_ENTRIES = [{ href: '/debug/library/button', label: 'Button' }] as const

export const ComponentLibraryScreen = () => {
  return (
    <ScrollView contentContainerClassName="gap-6 px-5 py-6">
      <DebugSection title="Components">
        {COMPONENT_LIBRARY_ENTRIES.map(entry => (
          <LibraryLinkRow key={entry.href} href={entry.href} label={entry.label} />
        ))}
      </DebugSection>
    </ScrollView>
  )
}
