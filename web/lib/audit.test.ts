import { afterEach, describe, expect, it, vi } from "vitest"

import {
  fetchBallot,
  formatClock,
  normalizeSectionKey,
  rejectionReason,
  requestTamper,
} from "@/lib/audit"
import { makeBallot } from "@/test/audit"
import { respond, stubFetch } from "@/test/fetch"

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("normalizeSectionKey", () => {
  it("pads and uppercases a typed key", () => {
    expect(normalizeSectionKey(" sp-71072-1-42 ")).toBe("SP-71072-0001-0042")
  })

  it("rejects anything else", () => {
    expect(normalizeSectionKey("SP 71072")).toBeNull()
    expect(normalizeSectionKey("SPX-1-1-1")).toBeNull()
  })
})

describe("rejectionReason", () => {
  it("translates the worker's reasons", () => {
    expect(rejectionReason("invalid signature")).toBe("Assinatura inválida")
    expect(rejectionReason("malformed entry")).toBe("Entrada malformada")
    expect(rejectionReason("invalid payload: KeyError('section')")).toBe(
      "Conteúdo ilegível"
    )
    expect(rejectionReason("something new")).toBe("something new")
  })
})

describe("formatClock", () => {
  it("shows Brasília time", () => {
    expect(formatClock("2026-10-04T20:03:09Z")).toBe("17:03:09")
  })
})

describe("fetchBallot", () => {
  it("reads a section or a random one", async () => {
    const fetchMock = stubFetch(
      respond(200, makeBallot()),
      respond(200, makeBallot())
    )

    expect(await fetchBallot(2, "SP-71072-0001-0042")).toEqual({
      status: "found",
      ballot: makeBallot(),
    })
    await fetchBallot(1, null)

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "http://127.0.0.1:8000/rounds/2/sections/SP-71072-0001-0042",
      "http://127.0.0.1:8000/rounds/1/sections/random",
    ])
  })

  it("tells a missing section from a failure", async () => {
    stubFetch(respond(404), respond(503), new TypeError("offline"))

    expect(await fetchBallot(1, null)).toEqual({ status: "missing" })
    expect(await fetchBallot(1, null)).toEqual({ status: "error" })
    expect(await fetchBallot(1, null)).toEqual({ status: "error" })
  })
})

describe("requestTamper", () => {
  it("posts a tampered ballot to the live round", async () => {
    const tampered = {
      section: "AC-10025-0001-0002",
      source: "SP-71072-0001-0042",
    }
    const fetchMock = stubFetch(respond(202, tampered))

    expect(await requestTamper(1)).toEqual({ status: "sent", tampered })
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/rounds/1/tamper",
      { method: "POST" }
    )
  })

  it("reports when nothing can be tampered with or the request fails", async () => {
    stubFetch(respond(409), respond(403), new TypeError("offline"))

    expect(await requestTamper(1)).toEqual({ status: "unavailable" })
    expect(await requestTamper(1)).toEqual({ status: "error" })
    expect(await requestTamper(1)).toEqual({ status: "error" })
  })
})
