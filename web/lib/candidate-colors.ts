export const CANDIDATE_PALETTE_SIZE = 6
export const NEUTRAL_CANDIDATE_COLOR = "var(--candidate-other)"

export function palette(...groups: ReadonlyArray<readonly number[]>): number[] {
  return [...new Set(groups.flat())].sort((a, b) => a - b)
}

export function candidateColor(
  universe: readonly number[],
  number: number
): string {
  const index = universe.indexOf(number)
  if (index < 0 || index >= CANDIDATE_PALETTE_SIZE) {
    return NEUTRAL_CANDIDATE_COLOR
  }
  return `var(--candidate-${index + 1})`
}
