import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useReplay, type ReplayClock } from "@/hooks/use-replay"
import { BASE_DURATION_MS } from "@/lib/replay"

function fakeClock() {
  let now = 0
  let tick: (() => void) | null = null
  const clock: ReplayClock = {
    now: () => now,
    schedule: (next) => {
      tick = next
      return () => {
        tick = null
      }
    },
  }
  return {
    clock,
    elapse(ms: number) {
      now += ms
      act(() => tick?.())
    },
    get scheduled() {
      return tick !== null
    },
  }
}

describe("useReplay", () => {
  it("plays from the start to the end at the base duration", () => {
    const fake = fakeClock()
    const { result } = renderHook(() => useReplay(fake.clock))
    expect(result.current[0]).toEqual({ status: "idle", fraction: 0, speed: 1 })

    act(() => result.current[1].start())
    expect(fake.scheduled).toBe(true)
    fake.elapse(BASE_DURATION_MS / 4)
    expect(result.current[0]).toMatchObject({
      status: "playing",
      fraction: 0.25,
    })

    fake.elapse(BASE_DURATION_MS)
    expect(result.current[0]).toMatchObject({ status: "finished", fraction: 1 })
    expect(fake.scheduled).toBe(false)
  })

  it("pauses, resumes, changes speed and seeks", () => {
    const fake = fakeClock()
    const { result } = renderHook(() => useReplay(fake.clock))
    act(() => result.current[1].start())
    fake.elapse(BASE_DURATION_MS / 10)

    act(() => result.current[1].pause())
    expect(fake.scheduled).toBe(false)
    expect(result.current[0].status).toBe("paused")

    act(() => result.current[1].setSpeed(4))
    act(() => result.current[1].resume())
    fake.elapse(BASE_DURATION_MS / 10)
    expect(result.current[0].fraction).toBeCloseTo(0.5)

    act(() => result.current[1].seek(0.9))
    expect(result.current[0].fraction).toBe(0.9)
    act(() => result.current[1].seek(5))
    expect(result.current[0].fraction).toBe(1)
  })

  it("restarts from a finished replay and leaves on stop", () => {
    const fake = fakeClock()
    const { result } = renderHook(() => useReplay(fake.clock))
    act(() => result.current[1].start())
    fake.elapse(BASE_DURATION_MS * 2)
    expect(result.current[0].status).toBe("finished")

    act(() => result.current[1].seek(0.5))
    expect(result.current[0].status).toBe("paused")

    act(() => result.current[1].resume())
    act(() => result.current[1].pause())
    act(() => result.current[1].seek(1))
    act(() => result.current[1].resume())
    fake.elapse(BASE_DURATION_MS)
    expect(result.current[0].status).toBe("finished")

    act(() => result.current[1].resume())
    expect(result.current[0]).toMatchObject({ status: "playing", fraction: 0 })

    act(() => result.current[1].stop())
    expect(result.current[0].status).toBe("idle")
    expect(fake.scheduled).toBe(false)
  })

  it("ticks on a timer by default", () => {
    const { result, unmount } = renderHook(() => useReplay())

    act(() => result.current[1].start())
    expect(result.current[0].status).toBe("playing")

    unmount()
  })
})
