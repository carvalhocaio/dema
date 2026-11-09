"use client"

import { useCallback, useLayoutEffect, useRef } from "react"

type Key = string | number

const DURATION_MS = 450
const EASING = "cubic-bezier(0.2, 0, 0, 1)"

export function useFlip<T extends HTMLElement>(keys: readonly Key[]) {
  const nodes = useRef(new Map<Key, T>())
  const offsets = useRef(new Map<Key, number>())
  const order = keys.join("|")

  useLayoutEffect(() => {
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches

    nodes.current.forEach((node, key) => {
      const previous = offsets.current.get(key)
      const next = node.offsetTop
      offsets.current.set(key, next)
      if (previous === undefined || previous === next || reduceMotion) return
      node.animate(
        [
          { transform: `translateY(${previous - next}px)` },
          { transform: "translateY(0)" },
        ],
        { duration: DURATION_MS, easing: EASING }
      )
    })
  }, [order])

  return useCallback(
    (key: Key) => (node: T | null) => {
      if (node) nodes.current.set(key, node)
      else nodes.current.delete(key)
    },
    []
  )
}
