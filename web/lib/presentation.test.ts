import { describe, expect, it } from "vitest"

import { candidateColor } from "@/lib/candidate-colors"
import { connectionStatus } from "@/lib/connection"
import type { Candidate } from "@/lib/results"

const candidate = (number: number): Candidate => ({
  number,
  name: `C${number}`,
  party: "P",
  votes: 0,
  share: 0,
})

describe("candidateColor", () => {
  it("depends on the ballot number, not on the ranking order", () => {
    const ranked = [candidate(99), candidate(27), candidate(12)]
    const reranked = [candidate(12), candidate(99), candidate(27)]
    expect(candidateColor(ranked, 27)).toBe("var(--candidate-2)")
    expect(candidateColor(reranked, 27)).toBe("var(--candidate-2)")
    expect(candidateColor(ranked, 12)).toBe("var(--candidate-1)")
  })

  it("falls back to a neutral color beyond the palette", () => {
    const many = [1, 2, 3, 4, 5, 6, 7, 8].map(candidate)
    expect(candidateColor(many, 6)).toBe("var(--candidate-6)")
    expect(candidateColor(many, 7)).toBe("var(--candidate-other)")
    expect(candidateColor(many, 8)).toBe("var(--candidate-other)")
    expect(candidateColor(many, 99)).toBe("var(--candidate-other)")
  })
})

describe("connectionStatus", () => {
  it("maps connection and setup to a label", () => {
    expect(connectionStatus("live", "ready")).toEqual({
      label: "Ao vivo",
      tone: "live",
    })
    expect(connectionStatus("live", "pending").label).toBe("Aguardando setup")
    expect(connectionStatus("reconnecting", "ready").tone).toBe("warning")
    expect(connectionStatus("unavailable", "unknown").label).toBe("Sem conexão")
    expect(connectionStatus("connecting", "unknown").label).toBe("Conectando")
  })
})
