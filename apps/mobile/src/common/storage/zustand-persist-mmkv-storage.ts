import { createJSONStorage, type StateStorage } from 'zustand/middleware'

import { appStorage } from '@/common/storage/mmkv'

const zustandPersistMmkvStorage: StateStorage = {
  getItem: name => appStorage.getString(name) ?? null,
  setItem: (name, value) => {
    appStorage.set(name, value)
  },
  removeItem: name => {
    appStorage.remove(name)
  },
}

export const createZustandPersistMmkvStorage = <T>() =>
  createJSONStorage<T>(() => zustandPersistMmkvStorage)
