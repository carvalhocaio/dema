import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { useRoundResults } from "@/hooks/use-round-results"
import { FakeEventSource } from "@/test/event-source"
import { makeResults } from "@/test/fixtures"
import { respond, stubFetch, type FetchResponse } from "@/test/fetch"

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal("EventSource", FakeEventSource)
})

describe("useRoundResults for the live round", () => {
  it("paints the snapshot before the first event", async () => {
    const results = makeResults({ round: 2 })
    const fetchMock = stubFetch(respond(200, results))

    const { result } = renderHook(() => useRoundResults(2, true))

    expect(result.current).toEqual({
      results: null,
      connection: "connecting",
      setup: "unknown",
    })
    await waitFor(() => expect(result.current.results).toEqual(results))
    expect(result.current.connection).toBe("live")
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/rounds/2/results",
      expect.objectContaining({ cache: "no-store" })
    )
    expect(FakeEventSource.latest().url).toBe(
      "http://127.0.0.1:8000/rounds/2/stream"
    )
  })

  it("flags a pending setup on 503 until the stream delivers results", async () => {
    stubFetch(respond(503))
    const { result } = renderHook(() => useRoundResults(1, true))
    await waitFor(() => expect(result.current.setup).toBe("pending"))

    const results = makeResults()
    act(() => FakeEventSource.latest().emit(results))

    expect(result.current).toEqual({
      results,
      connection: "live",
      setup: "ready",
    })
  })

  it("keeps a ready election when a late 503 arrives", async () => {
    stubFetch(respond(200, makeResults()), respond(503))
    const { result } = renderHook(() => useRoundResults(1, true))
    await waitFor(() => expect(result.current.setup).toBe("ready"))

    act(() => FakeEventSource.latest().open())

    await waitFor(() => expect(result.current.connection).toBe("live"))
    expect(result.current.setup).toBe("ready")
  })

  it("leaves the connection to the stream when snapshots fail", async () => {
    const fetchMock = stubFetch(respond(500), new TypeError("offline"))
    const { result } = renderHook(() => useRoundResults(1, true))

    act(() => FakeEventSource.latest().open())

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(result.current).toMatchObject({ results: null, connection: "live" })
  })

  it("follows the connection through outages and reconnections", () => {
    stubFetch(respond(500), respond(500), respond(500))
    const { result } = renderHook(() => useRoundResults(1, true))
    const source = FakeEventSource.latest()

    act(() => source.fail(FakeEventSource.CONNECTING))
    expect(result.current.connection).toBe("unavailable")

    act(() => source.open())
    act(() => source.fail(FakeEventSource.CONNECTING))
    expect(result.current.connection).toBe("reconnecting")

    const reconnecting = result.current
    act(() => source.fail(FakeEventSource.CONNECTING))
    expect(result.current).toBe(reconnecting)

    act(() => source.fail(FakeEventSource.CLOSED))
    expect(result.current.connection).toBe("unavailable")

    act(() => source.open())
    act(() => source.fail(FakeEventSource.CLOSED))
    expect(result.current.connection).toBe("unavailable")
  })

  it("closes the stream and drops in-flight snapshots on unmount", async () => {
    let release: (response: FetchResponse) => void = () => {}
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<FetchResponse>((resolve) => (release = resolve)))
    )
    const { result, unmount } = renderHook(() => useRoundResults(1, true))
    const source = FakeEventSource.latest()

    unmount()
    await act(async () => release(respond(200, makeResults())))

    expect(source.readyState).toBe(FakeEventSource.CLOSED)
    expect(result.current.results).toBeNull()
  })
})

describe("useRoundResults for a finished round", () => {
  it("fetches once without opening a stream", async () => {
    const results = makeResults({ verdict: "runoff", finalists: [27, 99] })
    stubFetch(respond(200, results))

    const { result } = renderHook(() => useRoundResults(1, false))

    await waitFor(() =>
      expect(result.current).toEqual({
        results,
        connection: "final",
        setup: "ready",
      })
    )
    expect(FakeEventSource.instances).toHaveLength(0)
  })

  it("reports an unreachable archive", async () => {
    stubFetch(new TypeError("offline"))

    const { result } = renderHook(() => useRoundResults(1, false))

    await waitFor(() => expect(result.current.connection).toBe("unavailable"))
  })
})
