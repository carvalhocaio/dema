import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ROUNDS_REFRESH_MS, useRounds } from "@/hooks/use-rounds"
import { respond, stubFetch } from "@/test/fetch"

const FIRST = [{ round: 1, status: "live" }]
const BOTH = [
  { round: 1, status: "final" },
  { round: 2, status: "live" },
]

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

async function flush() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0)
  })
}

async function tick() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ROUNDS_REFRESH_MS)
  })
}

describe("useRounds", () => {
  it("loads the rounds and keeps them fresh", async () => {
    const fetchMock = stubFetch(respond(200, FIRST), respond(200, BOTH))
    const { result } = renderHook(() => useRounds())
    expect(result.current).toMatchObject({ status: "loading", rounds: [] })

    await flush()
    expect(result.current).toMatchObject({ status: "ready", rounds: FIRST })

    await tick()
    expect(result.current.rounds).toEqual(BOTH)
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/rounds",
      expect.objectContaining({ cache: "no-store" })
    )
  })

  it("reloads on demand", async () => {
    const fetchMock = stubFetch(respond(200, FIRST), respond(200, BOTH))
    const { result } = renderHook(() => useRounds())
    await flush()

    act(() => result.current.refresh())
    await flush()

    expect(result.current.rounds).toEqual(BOTH)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it("keeps the same state when nothing changed", async () => {
    stubFetch(respond(200, FIRST), respond(200, FIRST))
    const { result } = renderHook(() => useRounds())
    await flush()
    const ready = result.current

    await tick()

    expect(result.current).toBe(ready)
  })

  it("keeps the last rounds while the API is unreachable and recovers", async () => {
    stubFetch(
      respond(200, FIRST),
      respond(500),
      new TypeError("offline"),
      respond(200, FIRST)
    )
    const { result } = renderHook(() => useRounds())
    await flush()

    await tick()
    expect(result.current).toMatchObject({
      status: "unavailable",
      rounds: FIRST,
    })
    await tick()
    expect(result.current.status).toBe("unavailable")
    await tick()
    expect(result.current).toMatchObject({ status: "ready", rounds: FIRST })
  })

  it("stops polling on unmount and ignores the aborted request", async () => {
    const fetchMock = stubFetch(new DOMException("aborted", "AbortError"))
    const { result, unmount } = renderHook(() => useRounds())

    unmount()
    await flush()
    await tick()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(result.current.status).toBe("loading")
  })
})
