import { renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useRejected } from "@/hooks/use-rejected"
import { makeRejection } from "@/test/audit"
import { respond, stubFetch } from "@/test/fetch"

describe("useRejected", () => {
  it("loads the rejections again when the revision changes", async () => {
    const first = [makeRejection()]
    const second = [makeRejection({ entry: "2-0" }), ...first]
    const fetchMock = stubFetch(respond(200, first), respond(200, second))
    const { result, rerender } = renderHook(
      ({ revision }) => useRejected(1, revision),
      { initialProps: { revision: 1 } }
    )
    await waitFor(() => expect(result.current).toEqual(first))

    rerender({ revision: 2 })

    await waitFor(() => expect(result.current).toEqual(second))
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/rounds/1/rejected",
      expect.objectContaining({ cache: "no-store" })
    )
  })

  it("keeps the last list when a refresh fails", async () => {
    const first = [makeRejection()]
    const fetchMock = stubFetch(
      respond(200, first),
      respond(500),
      new TypeError("offline")
    )
    const { result, rerender } = renderHook(
      ({ revision }) => useRejected(1, revision),
      { initialProps: { revision: 1 } }
    )
    await waitFor(() => expect(result.current).toEqual(first))

    rerender({ revision: 2 })
    rerender({ revision: 3 })

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(result.current).toEqual(first)
  })
})
