import { describe, expect, it } from "vitest"

import { candidateColor, palette } from "@/lib/candidate-colors"
import { connectionStatus, LIVE_STATUS, sameReport } from "@/lib/connection"

describe("palette", () => {
  it("merges candidate numbers from every round in ballot order", () => {
    expect(palette([99, 27, 12], [27, 31])).toEqual([12, 27, 31, 99])
    expect(palette()).toEqual([])
  })
})

describe("candidateColor", () => {
  it("depends on the ballot number within the universe, not on the ranking", () => {
    const universe = palette([12, 27, 31, 44, 99])
    expect(candidateColor(universe, 27)).toBe("var(--candidate-2)")
    expect(candidateColor(universe, 99)).toBe("var(--candidate-5)")
  })

  it("falls back to a neutral color beyond the palette or outside the universe", () => {
    const universe = [1, 2, 3, 4, 5, 6, 7]
    expect(candidateColor(universe, 6)).toBe("var(--candidate-6)")
    expect(candidateColor(universe, 7)).toBe("var(--candidate-other)")
    expect(candidateColor(universe, 99)).toBe("var(--candidate-other)")
  })
})

describe("connectionStatus", () => {
  it("maps connection and setup to a label", () => {
    expect(connectionStatus("live", "ready")).toBe(LIVE_STATUS)
    expect(connectionStatus("live", "pending").label).toBe("Aguardando setup")
    expect(connectionStatus("reconnecting", "ready").tone).toBe("warning")
    expect(connectionStatus("unavailable", "unknown").label).toBe("Sem conexão")
    expect(connectionStatus("connecting", "unknown").label).toBe("Conectando")
    expect(connectionStatus("final", "ready")).toEqual({
      label: "Resultado final",
      tone: "idle",
    })
  })
})

describe("sameReport", () => {
  const report = { label: "Ao vivo", tone: "live" as const, year: 2026 }

  it("compares label, tone and year", () => {
    expect(sameReport(report, { ...report })).toBe(true)
    expect(sameReport(report, { ...report, label: "Conectando" })).toBe(false)
    expect(sameReport(report, { ...report, tone: "idle" })).toBe(false)
    expect(sameReport(report, { ...report, year: null })).toBe(false)
  })
})
