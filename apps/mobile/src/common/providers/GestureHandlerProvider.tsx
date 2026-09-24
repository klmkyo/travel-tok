import type { ReactNode } from 'react'
import { GestureHandlerRootView } from 'react-native-gesture-handler'

export const GestureHandlerProvider = ({ children }: Props) => {
  return <GestureHandlerRootView style={{ flex: 1 }}>{children}</GestureHandlerRootView>
}

type Props = {
  children: ReactNode
}
