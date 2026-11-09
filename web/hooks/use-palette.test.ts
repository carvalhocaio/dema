import { renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { usePalette } from "@/hooks/use-palette"
import { respond, stubFetch } from "@/test/fetch"
import { makeCandidate, makeResults } from "@/test/fixtures"

const RUNOFF = makeResults({
  round: 2,
  candidates: [makeCandidate({ number: 31 }), makeCandidate({ number: 27 })],
})

describe("usePalette", () => {
  it("keeps colors stable by adding the first-round candidates", async () => {
    stubFetch(
      respond(
        200,
        makeResults({
          candidates: [12, 27, 31, 99].map((number) =>
            makeCandidate({ number })
          ),
        })
      )
    )

    const { result } = renderHook(() => usePalette(true, RUNOFF))

    expect(result.current).toEqual([27, 31])
    await waitFor(() => expect(result.current).toEqual([12, 27, 31, 99]))
  })

  it("uses only the current round without a first round or results", () => {
    const fetchMock = stubFetch()

    const { result, rerender } = renderHook(
      ({ results }) => usePalette(false, results),
      { initialProps: { results: RUNOFF as typeof RUNOFF | null } }
    )
    expect(result.current).toEqual([27, 31])
    rerender({ results: null })

    expect(result.current).toEqual([])
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("ignores a missing or unreachable first round", async () => {
    const fetchMock = stubFetch(respond(404))
    const { result, unmount } = renderHook(() => usePalette(true, RUNOFF))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    unmount()

    stubFetch(new TypeError("offline"))
    const second = renderHook(() => usePalette(true, RUNOFF))
    await waitFor(() => expect(second.result.current).toEqual([27, 31]))
    expect(result.current).toEqual([27, 31])
  })
})
