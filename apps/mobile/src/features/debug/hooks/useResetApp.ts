import { useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { Alert, DevSettings } from 'react-native'

import { isExpoDev } from '@/common/helpers/is-expo-dev'
import { appStorage } from '@/common/storage/mmkv'

const getErrorMessage = (error: unknown): string => {
  return error instanceof Error ? error.message : String(error)
}

export const useResetApp = () => {
  const queryClient = useQueryClient()

  return useCallback(() => {
    const failureMessages: string[] = []

    try {
      appStorage.clearAll()
    } catch (caughtError) {
      console.warn('Failed to clear app storage', caughtError)
      failureMessages.push(`Failed to clear app storage: ${getErrorMessage(caughtError)}`)
    }

    try {
      queryClient.clear()
    } catch (caughtError) {
      console.warn('Failed to clear the query cache', caughtError)
      failureMessages.push(`Failed to clear the query cache: ${getErrorMessage(caughtError)}`)
    }

    if (failureMessages.length > 0) {
      Alert.alert('Reset failed', failureMessages.join('\n\n'))
    }

    if (isExpoDev()) {
      DevSettings.reload()
      return
    }

    Alert.alert(
      'Reset complete',
      'Local data was cleared. Close and reopen the app to finish resetting.',
    )
  }, [queryClient])
}
