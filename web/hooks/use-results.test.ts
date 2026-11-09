import { act, renderHook, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useResults } from "@/hooks/use-results"
import { FakeEventSource } from "@/test/event-source"
import { makeResults } from "@/test/fixtures"

type FetchResponse = { status: number; ok: boolean; json: () => unknown }

function respond(status: number, body: unknown = {}): FetchResponse {
  return { status, ok: status >= 200 && status < 300, json: () => body }
}

function stubFetch(...responses: Array<FetchResponse | Error>) {
  const queue = [...responses]
  const fetchMock = vi.fn(async () => {
    const next = queue.shift() ?? respond(200, makeResults())
    if (next instanceof Error) throw next
    return next
  })
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal("EventSource", FakeEventSource)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("useResults", () => {
  it("starts connecting and paints the snapshot before the first event", async () => {
    const results = makeResults()
    const fetchMock = stubFetch(respond(200, results))

    const { result } = renderHook(() => useResults())

    expect(result.current).toEqual({
      results: null,
      connection: "connecting",
      setup: "unknown",
    })
    await waitFor(() => expect(result.current.results).toEqual(results))
    expect(result.current.setup).toBe("ready")
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/results",
      expect.objectContaining({ cache: "no-store" })
    )
    expect(FakeEventSource.latest().url).toBe(
      "http://127.0.0.1:8000/results/stream"
    )
  })

  it("flags a pending setup on 503 until the stream delivers results", async () => {
    stubFetch(respond(503))
    const { result } = renderHook(() => useResults())
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
    const { result } = renderHook(() => useResults())
    await waitFor(() => expect(result.current.setup).toBe("ready"))

    act(() => FakeEventSource.latest().open())

    await waitFor(() => expect(result.current.connection).toBe("live"))
    expect(result.current.setup).toBe("ready")
  })

  it("ignores failed and unreachable snapshots", async () => {
    const fetchMock = stubFetch(respond(500), new TypeError("offline"))
    const { result } = renderHook(() => useResults())

    act(() => FakeEventSource.latest().open())

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(result.current.results).toBeNull()
    expect(result.current.setup).toBe("unknown")
  })

  it("follows the connection through outages and reconnections", async () => {
    stubFetch(respond(500), respond(500), respond(500))
    const { result } = renderHook(() => useResults())
    const source = FakeEventSource.latest()

    act(() => source.fail(FakeEventSource.CONNECTING))
    expect(result.current.connection).toBe("unavailable")

    act(() => source.open())
    expect(result.current.connection).toBe("live")

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
    const fetchMock = vi.fn(
      () => new Promise<FetchResponse>((resolve) => (release = resolve))
    )
    vi.stubGlobal("fetch", fetchMock)
    const { result, unmount } = renderHook(() => useResults())
    const source = FakeEventSource.latest()

    unmount()
    await act(async () => release(respond(200, makeResults())))

    expect(source.readyState).toBe(FakeEventSource.CLOSED)
    expect(result.current.results).toBeNull()
  })
})
