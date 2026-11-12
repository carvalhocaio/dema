import { act, renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useCurrentRun } from "@/hooks/use-current-run"
import { respond, stubFetch } from "@/test/fetch"

const CURRENT = {
  run: { id: 3, round: 1, seed: 40, status: "counting" },
  runs_enabled: true,
}

describe("useCurrentRun", () => {
  it("loads the current run and reloads on demand", async () => {
    const fetchMock = stubFetch(
      respond(200, CURRENT),
      respond(200, { ...CURRENT, runs_enabled: false })
    )
    const { result } = renderHook(() => useCurrentRun())

    await waitFor(() => expect(result.current.current).toEqual(CURRENT))
    act(() => result.current.refresh())

    await waitFor(() =>
      expect(result.current.current?.runs_enabled).toBe(false)
    )
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/runs/current",
      expect.objectContaining({ cache: "no-store" })
    )
  })

  it("stays empty when the API refuses or is unreachable", async () => {
    const fetchMock = stubFetch(respond(500), new TypeError("offline"))
    const { result } = renderHook(() => useCurrentRun())

    act(() => result.current.refresh())

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(result.current.current).toBeNull()
  })
})
