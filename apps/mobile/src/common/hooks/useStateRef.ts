import {
  type Dispatch,
  type RefObject,
  type SetStateAction,
  useCallback,
  useRef,
  useState,
} from 'react'

export const useStateRef = <T>(initialValue: T): [T, Dispatch<SetStateAction<T>>, RefObject<T>] => {
  const [state, setState] = useState<T>(initialValue)
  const ref = useRef<T>(initialValue)

  const setStateAndRef = useCallback((value: SetStateAction<T>) => {
    const newState = typeof value === 'function' ? (value as (prev: T) => T)(ref.current) : value

    ref.current = newState
    setState(newState)
  }, [])

  return [state, setStateAndRef, ref]
}
