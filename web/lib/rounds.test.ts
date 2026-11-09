import { describe, expect, it } from "vitest"

import {
  findRound,
  initialRound,
  liveRound,
  parseRoundParam,
  type Round,
} from "@/lib/rounds"

const FINAL: Round = { round: 1, status: "final" }
const LIVE: Round = { round: 2, status: "live" }

describe("rounds", () => {
  it("finds the live round and rounds by number", () => {
    expect(liveRound([FINAL, LIVE])).toBe(LIVE)
    expect(liveRound([FINAL])).toBeUndefined()
    expect(findRound([FINAL, LIVE], 1)).toBe(FINAL)
    expect(findRound([FINAL], null)).toBeUndefined()
  })

  it("parses only known rounds from the query string", () => {
    expect(parseRoundParam("?turno=2")).toBe(2)
    expect(parseRoundParam("?turno=1&x=y")).toBe(1)
    expect(parseRoundParam("?turno=3")).toBeNull()
    expect(parseRoundParam("?turno=abc")).toBeNull()
    expect(parseRoundParam("")).toBeNull()
  })

  it("prefers the requested round, then the live one, then the latest", () => {
    expect(initialRound([FINAL, LIVE], 1)).toBe(FINAL)
    expect(initialRound([FINAL, LIVE], 3)).toBe(LIVE)
    expect(initialRound([FINAL, LIVE], null)).toBe(LIVE)
    expect(
      initialRound([FINAL, { round: 2, status: "final" }], null)?.round
    ).toBe(2)
    expect(initialRound([], null)).toBeUndefined()
  })
})
