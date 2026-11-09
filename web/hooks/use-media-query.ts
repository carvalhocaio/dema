"use client"

import { useCallback, useSyncExternalStore } from "react"

export const DESKTOP_QUERY = "(min-width: 1024px)"

function serverMatches(): boolean {
  return false
}

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const media = window.matchMedia(query)
      media.addEventListener("change", onChange)
      return () => media.removeEventListener("change", onChange)
    },
    [query]
  )
  const matches = useCallback(() => window.matchMedia(query).matches, [query])
  return useSyncExternalStore(subscribe, matches, serverMatches)
}
