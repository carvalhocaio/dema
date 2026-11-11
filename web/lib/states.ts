import { formatPercent, type Candidate } from "@/lib/results"

export type Region =
  "north" | "northeast" | "center_west" | "southeast" | "south" | "abroad"

export type StateCandidate = { number: number; votes: number; share: number }

export type StateResult = {
  state: string
  region: Region
  counted_sections: number
  total_sections: number
  progress: number
  candidates: StateCandidate[]
  leader: number | null
}

export type States = { year: number; round: number; states: StateResult[] }

export type Tile = { state: string; column: number; row: number }

export const REGION_LABELS: Record<Region, string> = {
  north: "Norte",
  northeast: "Nordeste",
  center_west: "Centro-Oeste",
  southeast: "Sudeste",
  south: "Sul",
  abroad: "Exterior",
}

export const REGION_ORDER: readonly Region[] = [
  "north",
  "northeast",
  "center_west",
  "southeast",
  "south",
  "abroad",
]

export const GRID_COLUMNS = 9
export const GRID_ROWS = 8

export const TILES: readonly Tile[] = [
  { state: "RR", column: 2, row: 1 },
  { state: "AP", column: 4, row: 1 },
  { state: "AM", column: 1, row: 2 },
  { state: "PA", column: 3, row: 2 },
  { state: "MA", column: 5, row: 2 },
  { state: "CE", column: 6, row: 2 },
  { state: "RN", column: 7, row: 2 },
  { state: "AC", column: 1, row: 3 },
  { state: "RO", column: 2, row: 3 },
  { state: "TO", column: 4, row: 3 },
  { state: "PI", column: 5, row: 3 },
  { state: "PB", column: 7, row: 3 },
  { state: "PE", column: 7, row: 4 },
  { state: "MT", column: 3, row: 4 },
  { state: "BA", column: 5, row: 4 },
  { state: "AL", column: 8, row: 4 },
  { state: "SE", column: 7, row: 5 },
  { state: "GO", column: 4, row: 5 },
  { state: "DF", column: 5, row: 5 },
  { state: "MS", column: 3, row: 6 },
  { state: "MG", column: 5, row: 6 },
  { state: "ES", column: 6, row: 6 },
  { state: "SP", column: 4, row: 7 },
  { state: "RJ", column: 5, row: 7 },
  { state: "PR", column: 3, row: 7 },
  { state: "SC", column: 3, row: 8 },
  { state: "RS", column: 2, row: 8 },
  { state: "ZZ", column: 9, row: 8 },
]

const MIN_INTENSITY = 0.3

export function tileIntensity(progress: number): number {
  return progress <= 0 ? 0 : MIN_INTENSITY + (1 - MIN_INTENSITY) * progress
}

export function topTwo(result: StateResult): StateCandidate[] {
  return result.candidates.slice(0, 2)
}

export function byRegion(
  results: readonly StateResult[]
): Map<Region, StateResult[]> {
  const groups = new Map<Region, StateResult[]>()
  for (const region of REGION_ORDER) groups.set(region, [])
  for (const result of results) groups.get(result.region)?.push(result)
  return groups
}

export function statesSummary(
  states: States,
  candidates: readonly Candidate[]
): string {
  const name = (number: number | null) =>
    candidates.find((c) => c.number === number)?.name ?? "ninguém"
  const led = new Map<number | null, number>()
  for (const result of states.states) {
    led.set(result.leader, (led.get(result.leader) ?? 0) + 1)
  }
  const parts = [...led.entries()]
    .filter(([leader]) => leader !== null)
    .sort((a, b) => b[1] - a[1])
    .map(([leader, count]) => `${name(leader)} lidera em ${count}`)
  const pending = led.get(null) ?? 0
  const tail = pending > 0 ? `; ${pending} sem apuração` : ""
  return `Mapa por estado: ${parts.join(", ") || "nenhum estado apurado"}${tail}.`
}

export function describeTile(
  result: StateResult,
  candidates: readonly Candidate[]
): string {
  const name = (number: number) =>
    candidates.find((c) => c.number === number)?.name ?? String(number)
  const leaders = topTwo(result)
    .map((c) => `${name(c.number)} ${formatPercent(c.share)}`)
    .join(", ")
  return `${result.state}: ${formatPercent(result.progress)} apurado. ${leaders || "Sem votos"}.`
}
