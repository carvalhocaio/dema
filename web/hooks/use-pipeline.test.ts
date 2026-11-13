import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { PIPELINE_POLL_MS, usePipeline } from "@/hooks/use-pipeline"
import { respond, stubFetch } from "@/test/fetch"
import { makePipeline } from "@/test/pipeline"

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

describe("usePipeline", () => {
  it("loads the metrics right away", async () => {
    const pipeline = makePipeline()
    const fetchMock = stubFetch(respond(200, pipeline))

    const { result } = renderHook(() => usePipeline())
    await advance(0)

    expect(result.current.pipeline).toEqual(pipeline)
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/pipeline",
      expect.objectContaining({ cache: "no-store" })
    )
  })

  it("polls while the live stream is silent", async () => {
    const fetchMock = stubFetch(
      respond(503),
      respond(200, makePipeline({ rate: 10 }))
    )
    const { result } = renderHook(() => usePipeline())
    await advance(0)
    expect(result.current.pipeline).toBeNull()

    await advance(PIPELINE_POLL_MS)

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result.current.pipeline?.rate).toBe(10)
  })

  it("stops polling while the stream pushes metrics", async () => {
    const fetchMock = stubFetch(respond(200, makePipeline()))
    const { result } = renderHook(() => usePipeline())
    await advance(0)

    act(() => result.current.receive(makePipeline({ rate: 99 })))
    await advance(PIPELINE_POLL_MS)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(result.current.pipeline?.rate).toBe(99)
  })

  it("keeps the last metrics when the API is unreachable", async () => {
    stubFetch(respond(200, makePipeline()), new TypeError("offline"))
    const { result } = renderHook(() => usePipeline())
    await advance(PIPELINE_POLL_MS)

    expect(result.current.pipeline).toEqual(makePipeline())
  })

  it("stops polling once unmounted", async () => {
    const fetchMock = stubFetch()
    const { unmount } = renderHook(() => usePipeline())
    await advance(0)

    unmount()
    await advance(PIPELINE_POLL_MS * 3)

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
