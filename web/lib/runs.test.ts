import { describe, expect, it } from "vitest"

import { parseSeed, requestRun, RunRequestError } from "@/lib/runs"
import { respond, stubFetch } from "@/test/fetch"

describe("parseSeed", () => {
  it("treats an empty field as a drawn seed", () => {
    expect(parseSeed("")).toBeNull()
    expect(parseSeed("   ")).toBeNull()
  })

  it("accepts non-negative integers", () => {
    expect(parseSeed(" 42 ")).toBe(42)
    expect(parseSeed("0")).toBe(0)
  })

  it.each(["-1", "1.5", "abc"])("rejects %s", (value) => {
    expect(() => parseSeed(value)).toThrow(RunRequestError)
  })
})

describe("requestRun", () => {
  it("posts the seed when there is one", async () => {
    const run = { id: 3, round: 1, seed: 7, status: "preparing" }
    const fetchMock = stubFetch(respond(202, run))

    await expect(requestRun(7)).resolves.toEqual(run)

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/runs",
      expect.objectContaining({ method: "POST", body: '{"seed":7}' })
    )
  })

  it("lets the server draw the seed", async () => {
    const fetchMock = stubFetch(respond(202, { id: 4 }))

    await requestRun(null)

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ body: "{}" })
  })

  it("explains refusals", async () => {
    stubFetch(respond(403))

    await expect(requestRun(null)).rejects.toThrow(
      "Não foi possível iniciar a apuração."
    )
  })
})
