// oxlint-disable-next-line no-restricted-imports -- wrapper re-exports the restricted host
import { SafeAreaView as RNSafeAreaView } from 'react-native-safe-area-context'
import { withUniwind } from 'uniwind'

export const SafeAreaView = withUniwind(RNSafeAreaView)
