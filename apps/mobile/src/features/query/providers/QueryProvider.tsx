import {
  QueryClient,
  QueryClientProvider,
  focusManager,
  noop,
  onlineManager,
} from '@tanstack/react-query'
import * as Network from 'expo-network'
import { type ReactNode, useEffect, useState } from 'react'
import { AppState } from 'react-native'

export const QueryProvider = ({ children }: QueryProviderProps) => {
  const [queryClient] = useState(() => new QueryClient())

  // Auto refetch on reconnect. Already automatic on web, for native we gotta wire it up.
  // https://tanstack.com/query/latest/docs/framework/react/react-native#online-status-management
  useEffect(() => {
    onlineManager.setEventListener(setOnline => {
      let hasListenerReported = false

      const subscription = Network.addNetworkStateListener(state => {
        hasListenerReported = true
        setOnline(!!state.isConnected)
      })

      // Ignore the initial read if the listener has already reported newer state.
      Network.getNetworkStateAsync()
        .then(state => {
          if (!hasListenerReported) {
            setOnline(!!state.isConnected)
          }
        })
        .catch(noop)

      return () => {
        subscription.remove()
      }
    })
  }, [])

  // Auto refetch when user relaunches the app. Also automatically done on web, but here
  // we gotta notify Tanstacks focusManager about it.
  // https://tanstack.com/query/latest/docs/framework/react/react-native#refetch-on-app-focus
  useEffect(() => {
    const appStateSubscription = AppState.addEventListener('change', status => {
      // used for refetches
      focusManager.setFocused(status === 'active')
    })

    return () => {
      appStateSubscription.remove()
    }
  }, [])

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

type QueryProviderProps = {
  children: ReactNode
}
