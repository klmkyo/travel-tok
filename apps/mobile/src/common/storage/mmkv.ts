import { createMMKV } from 'react-native-mmkv'

// Used the default storage. We get it here so we can use it for zustand etc.
export const appStorage = createMMKV()
