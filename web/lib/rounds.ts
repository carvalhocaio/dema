export type RoundStatus = "live" | "final"

export type Round = {
  round: number
  status: RoundStatus
}

export const ROUND_NUMBERS = [1, 2] as const
export const ROUND_PARAM = "turno"

export function liveRound(rounds: readonly Round[]): Round | undefined {
  return rounds.find((round) => round.status === "live")
}

export function findRound(
  rounds: readonly Round[],
  number: number | null
): Round | undefined {
  return rounds.find((round) => round.round === number)
}

export function parseRoundParam(search: string): number | null {
  const value = Number(new URLSearchParams(search).get(ROUND_PARAM))
  return ROUND_NUMBERS.some((round) => round === value) ? value : null
}

export function initialRound(
  rounds: readonly Round[],
  requested: number | null
): Round | undefined {
  return findRound(rounds, requested) ?? liveRound(rounds) ?? rounds.at(-1)
}
