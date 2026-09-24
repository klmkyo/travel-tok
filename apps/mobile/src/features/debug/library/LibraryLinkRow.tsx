import { Link, type Href } from 'expo-router'
import { Pressable } from 'react-native'

import { IconSymbol } from '@/common/components/icon-symbol/IconSymbol'
import { ThemedText } from '@/common/components/themed-text/ThemedText'

export const LibraryLinkRow = ({ href, label }: LibraryLinkRowProps) => {
  return (
    <Link href={href} asChild>
      <Pressable className="flex-row items-center justify-between gap-4">
        <ThemedText className="flex-1 text-base font-medium tracking-wide">{label}</ThemedText>
        <IconSymbol
          name={{
            ios: 'chevron.right',
            android: 'chevron_right',
          }}
          size={16}
          colorClassName="accent-base-500"
        />
      </Pressable>
    </Link>
  )
}

type LibraryLinkRowProps = {
  href: Href
  label: string
}
