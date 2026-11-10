"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { advance, clampFraction, type ReplaySpeed } from "@/lib/replay"

export type ReplayClock = {
  now: () => number
  schedule: (tick: () => void) => () => void
}

export type ReplayStatus = "idle" | "playing" | "paused" | "finished"

export type ReplayState = {
  status: ReplayStatus
  fraction: number
  speed: ReplaySpeed
}

export type ReplayControls = {
  start: () => void
  pause: () => void
  resume: () => void
  stop: () => void
  seek: (fraction: number) => void
  setSpeed: (speed: ReplaySpeed) => void
}

const FRAME_MS = 50

export const frameClock: ReplayClock = {
  now: () => Date.now(),
  schedule: (tick) => {
    const timer = setInterval(tick, FRAME_MS)
    return () => clearInterval(timer)
  },
}

const INITIAL: ReplayState = { status: "idle", fraction: 0, speed: 1 }

export function useReplay(
  clock: ReplayClock = frameClock
): [ReplayState, ReplayControls] {
  const [state, setState] = useState<ReplayState>(INITIAL)
  const last = useRef(0)

  useEffect(() => {
    if (state.status !== "playing") return
    last.current = clock.now()
    return clock.schedule(() => {
      const now = clock.now()
      const elapsed = now - last.current
      last.current = now
      setState((current) => {
        const fraction = advance(current.fraction, elapsed, current.speed)
        return {
          ...current,
          fraction,
          status: fraction >= 1 ? "finished" : current.status,
        }
      })
    })
  }, [clock, state.status])

  const start = useCallback(
    () =>
      setState((current) => ({ ...current, status: "playing", fraction: 0 })),
    []
  )
  const pause = useCallback(
    () => setState((current) => ({ ...current, status: "paused" })),
    []
  )
  const resume = useCallback(
    () =>
      setState((current) => ({
        ...current,
        status: "playing",
        fraction: current.status === "finished" ? 0 : current.fraction,
      })),
    []
  )
  const stop = useCallback(() => setState(INITIAL), [])
  const seek = useCallback(
    (fraction: number) =>
      setState((current) => ({
        ...current,
        fraction: clampFraction(fraction),
        status: current.status === "finished" ? "paused" : current.status,
      })),
    []
  )
  const setSpeed = useCallback(
    (speed: ReplaySpeed) => setState((current) => ({ ...current, speed })),
    []
  )

  return [state, { start, pause, resume, stop, seek, setSpeed }]
}
