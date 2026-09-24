import { useEffect } from 'react'

/** Example global event. Remove when we add an actual global event. */
export const GlobalHelloWorldPrinter = () => {
  useEffect(() => {
    console.log('Hello world')
  }, [])

  return null
}
