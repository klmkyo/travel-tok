import type { ComponentType, ReactNode } from 'react'

import { GlobalHelloWorldPrinter } from '@/common/global-events/GlobalHelloWorldPrinter'

/**
 * For things that should be active for the lifetime of the app, only mounted once.
 */
const GLOBAL_EVENT_REGISTRY = [GlobalHelloWorldPrinter] satisfies readonly ComponentType[]

const GLOBAL_EVENTS = GLOBAL_EVENT_REGISTRY.map((component, id) => ({
  component,
  id,
}))

export const GlobalEventsProvider = ({ children }: Props) => {
  return (
    <>
      {children}

      {GLOBAL_EVENTS.map(entry => {
        const EventComponent = entry.component

        return <EventComponent key={entry.id} />
      })}
    </>
  )
}

type Props = {
  children: ReactNode
}
