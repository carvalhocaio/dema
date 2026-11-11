import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useStates } from "@/hooks/use-states"
import { TIMELINE_THROTTLE_MS as STATES_THROTTLE_MS } from "@/hooks/use-timeline"
import { respond, stubFetch } from "@/test/fetch"
import { makeStates } from "@/test/states"

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

describe("useStates", () => {
  it("loads the round timeline right away", async () => {
    const timeline = makeStates()
    const fetchMock = stubFetch(respond(200, timeline))

    const { result } = renderHook(() => useStates(1, null))
    await advance(0)

    expect(result.current).toEqual(timeline)
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/rounds/1/states",
      expect.objectContaining({ cache: "no-store" })
    )
  })

  it("refetches on new results at most once every two seconds", async () => {
    const fetchMock = stubFetch()
    const { rerender } = renderHook(({ revision }) => useStates(1, revision), {
      initialProps: { revision: 1 },
    })
    await advance(0)

    rerender({ revision: 2 })
    rerender({ revision: 3 })
    await advance(STATES_THROTTLE_MS - 1)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await advance(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it("keeps the last timeline when a refresh fails", async () => {
    const timeline = makeStates()
    stubFetch(respond(200, timeline), respond(500), new TypeError("offline"))
    const { result, rerender } = renderHook(
      ({ revision }) => useStates(1, revision),
      { initialProps: { revision: 1 } }
    )
    await advance(0)

    rerender({ revision: 2 })
    await advance(STATES_THROTTLE_MS)
    rerender({ revision: 3 })
    await advance(STATES_THROTTLE_MS)

    expect(result.current).toEqual(timeline)
  })

  it("aborts the request on unmount", async () => {
    const fetchMock = stubFetch()
    const { unmount } = renderHook(() => useStates(2, null))
    await advance(0)

    unmount()

    const init = fetchMock.mock.calls[0][1]
    expect(init?.signal?.aborted).toBe(true)
  })
})
