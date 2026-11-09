import type { Candidate } from "@/lib/results"

export const CANDIDATE_PALETTE_SIZE = 6
export const NEUTRAL_CANDIDATE_COLOR = "var(--candidate-other)"

export function candidateColor(
  candidates: readonly Candidate[],
  number: number
): string {
  const numbers = candidates.map((c) => c.number).sort((a, b) => a - b)
  const index = numbers.indexOf(number)
  if (index < 0 || index >= CANDIDATE_PALETTE_SIZE) {
    return NEUTRAL_CANDIDATE_COLOR
  }
  return `var(--candidate-${index + 1})`
}
