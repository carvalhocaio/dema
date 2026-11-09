import type { Candidate } from "@/lib/results"

export const CANDIDATE_PALETTE_SIZE = 6

export function candidateColor(
  candidates: readonly Candidate[],
  number: number
): string {
  const numbers = candidates.map((c) => c.number).sort((a, b) => a - b)
  const index = Math.max(numbers.indexOf(number), 0)
  return `var(--candidate-${(index % CANDIDATE_PALETTE_SIZE) + 1})`
}
