import { describe, expect, it } from "vitest"

import {
  finalistBadge,
  finalistCandidates,
  formatInteger,
  formatPercent,
  hasVerdict,
  isFinalist,
  ratio,
  roundLabel,
  verdictLabel,
  voteBreakdown,
  type Results,
} from "@/lib/results"

function makeResults(overrides: Partial<Results> = {}): Results {
  return {
    year: 2026,
    round: 1,
    progress: {
      counted_sections: 451203,
      total_sections: 516785,
      counted_electorate: 1000,
      total_electorate: 1200,
      ratio: 0.873,
      is_complete: false,
    },
    votes: {
      valid: 600,
      blank: 100,
      null: 100,
      turnout: 800,
      abstentions: 200,
    },
    candidates: [
      {
        number: 27,
        name: "Keons",
        party: "Torchbearers",
        votes: 350,
        share: 0.5833,
      },
      {
        number: 99,
        name: "Nico",
        party: "Dema Order",
        votes: 200,
        share: 0.3333,
      },
      {
        number: 13,
        name: "Lisden",
        party: "Vialism",
        votes: 50,
        share: 0.0833,
      },
    ],
    verdict: "undecided",
    finalists: [],
    ...overrides,
  }
}

describe("formatPercent", () => {
  it("uses pt-BR decimals with two digits", () => {
    expect(formatPercent(0.4796)).toBe("47,96%")
    expect(formatPercent(1)).toBe("100,00%")
    expect(formatPercent(0)).toBe("0,00%")
  })
})

describe("formatInteger", () => {
  it("groups thousands with dots", () => {
    expect(formatInteger(57786804)).toBe("57.786.804")
    expect(formatInteger(0)).toBe("0")
  })
})

describe("ratio", () => {
  it("returns zero when the whole is zero", () => {
    expect(ratio(10, 0)).toBe(0)
    expect(ratio(1, 4)).toBe(0.25)
  })
})

describe("roundLabel", () => {
  it("uses the ordinal indicator", () => {
    expect(roundLabel(1)).toBe("1º turno")
  })
})

describe("verdict helpers", () => {
  it("has no verdict while undecided", () => {
    const results = makeResults()
    expect(hasVerdict(results)).toBe(false)
    expect(verdictLabel(results)).toBeNull()
    expect(finalistBadge(results.verdict)).toBeNull()
    expect(isFinalist(results, 27)).toBe(false)
  })

  it("labels an elected candidate", () => {
    const results = makeResults({ verdict: "elected", finalists: [27] })
    expect(verdictLabel(results)).toBe("Eleito: Keons (27)")
    expect(finalistBadge(results.verdict)).toBe("Eleito")
    expect(isFinalist(results, 27)).toBe(true)
    expect(isFinalist(results, 99)).toBe(false)
  })

  it("labels a runoff in finalist order", () => {
    const results = makeResults({ verdict: "runoff", finalists: [27, 99] })
    expect(verdictLabel(results)).toBe("2º turno: Keons × Nico")
    expect(finalistBadge(results.verdict)).toBe("2º turno")
    expect(isFinalist(results, 99)).toBe(true)
    expect(isFinalist(results, 13)).toBe(false)
  })

  it("ignores finalists missing from the candidate list", () => {
    const results = makeResults({ verdict: "runoff", finalists: [27, 42] })
    expect(finalistCandidates(results).map((c) => c.number)).toEqual([27])
    expect(verdictLabel(results)).toBeNull()
  })
})

describe("voteBreakdown", () => {
  it("relates votes to turnout and turnout/abstention to the counted electorate", () => {
    const shares = Object.fromEntries(
      voteBreakdown(makeResults()).map((item) => [item.label, item.share])
    )
    expect(shares).toEqual({
      Válidos: 0.75,
      Brancos: 0.125,
      Nulos: 0.125,
      Comparecimento: 0.8,
      Abstenção: 0.2,
    })
  })
})
