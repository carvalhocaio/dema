export type Verdict = "undecided" | "elected" | "runoff"

export type Progress = {
  counted_sections: number
  total_sections: number
  counted_electorate: number
  total_electorate: number
  ratio: number
  is_complete: boolean
}

export type Votes = {
  valid: number
  blank: number
  null: number
  turnout: number
  abstentions: number
}

export type Candidate = {
  number: number
  name: string
  party: string
  votes: number
  share: number
}

export type Results = {
  year: number
  round: number
  progress: Progress
  votes: Votes
  candidates: Candidate[]
  verdict: Verdict
  finalists: number[]
}

export type BreakdownItem = {
  label: string
  value: number
  share: number
  basis: string
}

const LOCALE = "pt-BR"

const percentFormat = new Intl.NumberFormat(LOCALE, {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const integerFormat = new Intl.NumberFormat(LOCALE, {
  maximumFractionDigits: 0,
})

export function formatPercent(fraction: number): string {
  return percentFormat.format(fraction)
}

export function formatInteger(value: number): string {
  return integerFormat.format(value)
}

export function ratio(part: number, whole: number): number {
  return whole > 0 ? part / whole : 0
}

export function hasVerdict(results: Results): boolean {
  return results.verdict !== "undecided"
}

export function isFinalist(results: Results, number: number): boolean {
  return hasVerdict(results) && results.finalists.includes(number)
}

export function finalistBadge(verdict: Verdict): string | null {
  if (verdict === "elected") return "Eleito"
  if (verdict === "runoff") return "2º turno"
  return null
}

export function finalistCandidates(results: Results): Candidate[] {
  return results.finalists
    .map((number) => results.candidates.find((c) => c.number === number))
    .filter((candidate): candidate is Candidate => candidate !== undefined)
}

export function verdictLabel(results: Results): string | null {
  const [first, second] = finalistCandidates(results)
  if (results.verdict === "elected" && first) {
    return `Eleito: ${first.name} (${first.number})`
  }
  if (results.verdict === "runoff" && first && second) {
    return `2º turno: ${first.name} × ${second.name}`
  }
  return null
}

export function roundLabel(round: number): string {
  return `${round}º turno`
}

const OF_TURNOUT = "do comparecimento"
const OF_COUNTED_ELECTORATE = "do eleitorado apurado"

export function voteBreakdown(results: Results): BreakdownItem[] {
  const { votes, progress } = results
  return [
    {
      label: "Válidos",
      value: votes.valid,
      share: ratio(votes.valid, votes.turnout),
      basis: OF_TURNOUT,
    },
    {
      label: "Brancos",
      value: votes.blank,
      share: ratio(votes.blank, votes.turnout),
      basis: OF_TURNOUT,
    },
    {
      label: "Nulos",
      value: votes.null,
      share: ratio(votes.null, votes.turnout),
      basis: OF_TURNOUT,
    },
    {
      label: "Comparecimento",
      value: votes.turnout,
      share: ratio(votes.turnout, progress.counted_electorate),
      basis: OF_COUNTED_ELECTORATE,
    },
    {
      label: "Abstenção",
      value: votes.abstentions,
      share: ratio(votes.abstentions, progress.counted_electorate),
      basis: OF_COUNTED_ELECTORATE,
    },
  ]
}
