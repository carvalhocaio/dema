import { renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useReplayData } from "@/hooks/use-replay-data"
import { respond, routeFetch } from "@/test/fetch"
import { makeReplay } from "@/test/replay"

describe("useReplayData", () => {
  it("stays idle until wanted, then loads once", async () => {
    const replay = makeReplay()
    const fetchMock = routeFetch({
      "/rounds/1/replay": () => respond(200, replay),
    })
    const { result, rerender } = renderHook(
      ({ wanted }) => useReplayData(1, wanted),
      { initialProps: { wanted: false } }
    )
    expect(result.current).toEqual({ status: "idle", replay: null })
    expect(fetchMock).not.toHaveBeenCalled()

    rerender({ wanted: true })
    expect(result.current.status).toBe("loading")
    await waitFor(() => expect(result.current.status).toBe("ready"))
    expect(result.current.replay).toEqual(replay)

    rerender({ wanted: false })
    expect(result.current).toEqual({ status: "idle", replay: null })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("reports failures", async () => {
    routeFetch({ "/rounds/1/replay": () => respond(500) })
    const { result } = renderHook(() => useReplayData(1, true))

    await waitFor(() => expect(result.current.status).toBe("error"))
  })

  it("ignores an aborted request", async () => {
    routeFetch({ "/rounds/1/replay": () => new Error("offline") })
    const { result, unmount } = renderHook(() => useReplayData(1, true))
    unmount()

    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(result.current.status).toBe("loading")
  })
})
