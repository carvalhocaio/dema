import { act, renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { useBallotLookup } from "@/hooks/use-ballot-lookup"
import { makeBallot } from "@/test/audit"
import { respond, stubFetch, type FetchResponse } from "@/test/fetch"

describe("useBallotLookup", () => {
  it("normalizes the key and shows the counted ballot", async () => {
    const fetchMock = stubFetch(respond(200, makeBallot()))
    const { result } = renderHook(() => useBallotLookup(1))

    act(() => result.current.search("sp-71072-1-42"))

    expect(result.current.state).toEqual({ status: "loading" })
    await waitFor(() =>
      expect(result.current.state).toEqual({
        status: "found",
        ballot: makeBallot(),
      })
    )
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/rounds/1/sections/SP-71072-0001-0042"
    )
  })

  it("refuses malformed keys without asking the API", () => {
    const fetchMock = stubFetch()
    const { result } = renderHook(() => useBallotLookup(1))

    act(() => result.current.search("nope"))

    expect(result.current.state).toEqual({ status: "invalid" })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("says which section is still to count and when nothing was counted", async () => {
    stubFetch(respond(404), respond(404), respond(500))
    const { result } = renderHook(() => useBallotLookup(1))

    act(() => result.current.search("SP-71072-0001-0042"))
    await waitFor(() =>
      expect(result.current.state).toEqual({
        status: "missing",
        section: "SP-71072-0001-0042",
      })
    )
    act(() => result.current.draw())
    await waitFor(() =>
      expect(result.current.state).toEqual({ status: "missing", section: null })
    )
    act(() => result.current.draw())
    await waitFor(() =>
      expect(result.current.state).toEqual({ status: "error" })
    )
  })

  it("keeps only the answer to the latest request", async () => {
    let answerFirst: (response: FetchResponse) => void = () => {}
    const first = new Promise<FetchResponse>((resolve) => {
      answerFirst = resolve
    })
    const fetchMock = vi
      .fn<() => Promise<FetchResponse>>()
      .mockReturnValueOnce(first)
    vi.stubGlobal("fetch", fetchMock)
    const { result } = renderHook(() => useBallotLookup(1))

    act(() => result.current.draw())
    act(() => result.current.search("bad key"))
    await act(async () => answerFirst(respond(200, makeBallot())))

    expect(result.current.state).toEqual({ status: "invalid" })
  })
})
