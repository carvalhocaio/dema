import { formatPercent, type Candidate, type Verdict } from "@/lib/results"

export type TimelinePoint = {
  at: string
  progress: number
  shares: Record<string, number>
  verdict: Verdict
}

export type Timeline = {
  year: number
  round: number
  points: TimelinePoint[]
  decided_at: string | null
}

export type ChartRow = { progress: number; elapsed: number } & Record<
  string,
  number
>

export type Decision = { progress: number; elapsed: number }

export type DecisionLabelPosition = "insideTopLeft" | "insideTopRight"

export const MAJORITY = 0.5
export const PROGRESS_TICKS = [0, 0.25, 0.5, 0.75, 1]

const Y_STEP = 0.05
const Y_PADDING = 0.02
const MAX_Y_TICKS = 8
const MINUTE_MS = 60_000
const LABEL_FLIP_PROGRESS = 0.7

const percentTickFormat = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  maximumFractionDigits: 0,
})

const oneDecimalPercent = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
})

export function formatPercentTick(fraction: number): string {
  return percentTickFormat.format(fraction)
}

export function formatElapsed(ms: number): string {
  const minutes = Math.round(ms / MINUTE_MS)
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  return `${hours}h${String(minutes % 60).padStart(2, "0")}`
}

export function seriesKey(number: number): string {
  return `c${number}`
}

export function chartRows(timeline: Timeline): ChartRow[] {
  const start = Date.parse(timeline.points[0]?.at ?? "")
  return timeline.points.map((point) => {
    const row: ChartRow = {
      progress: point.progress,
      elapsed: Date.parse(point.at) - start,
    }
    for (const [number, share] of Object.entries(point.shares)) {
      row[seriesKey(Number(number))] = share
    }
    return row
  })
}

function toStep(value: number): number {
  return Math.round(value * 100) / 100
}

export function yDomain(
  rows: readonly ChartRow[],
  numbers: readonly number[]
): [number, number] {
  const values = rows.flatMap((row) => numbers.map((n) => row[seriesKey(n)]))
  const low = Math.min(MAJORITY, ...values) - Y_PADDING
  const high = Math.max(MAJORITY, ...values) + Y_PADDING
  return [
    toStep(Math.max(0, Math.floor(low / Y_STEP) * Y_STEP)),
    toStep(Math.min(1, Math.ceil(high / Y_STEP) * Y_STEP)),
  ]
}

export function yTicks([low, high]: readonly [number, number]): number[] {
  const step = (high - low) / Y_STEP > MAX_Y_TICKS ? Y_STEP * 2 : Y_STEP
  const first = Math.ceil(toStep(low / step)) * step
  const ticks: number[] = []
  for (let tick = first; tick <= high + 1e-9; tick += step) {
    ticks.push(toStep(tick))
  }
  return ticks
}

export function emphasizedNumbers(
  round: number,
  candidates: readonly Candidate[]
): number[] {
  const ranked = candidates.map((candidate) => candidate.number)
  return round === 1 ? ranked.slice(0, 2) : ranked
}

function leaderOf(row: ChartRow, candidates: readonly Candidate[]): Candidate {
  return candidates.reduce((best, candidate) =>
    row[seriesKey(candidate.number)] > row[seriesKey(best.number)]
      ? candidate
      : best
  )
}

export function leadSince(
  rows: readonly ChartRow[],
  candidates: readonly Candidate[]
): { leader: Candidate; since: number } {
  const leader = leaderOf(rows[rows.length - 1], candidates)
  let since = rows.length - 1
  while (since > 0 && leaderOf(rows[since - 1], candidates) === leader) {
    since -= 1
  }
  return { leader, since: rows[since].progress }
}

export function decision(timeline: Timeline | null): Decision | null {
  if (!timeline?.decided_at) return null
  const index = timeline.points.findIndex(
    (point) => point.at === timeline.decided_at
  )
  if (index < 0) return null
  const row = chartRows(timeline)[index]
  return { progress: row.progress, elapsed: row.elapsed }
}

export function decisionLabelPosition(progress: number): DecisionLabelPosition {
  return progress > LABEL_FLIP_PROGRESS ? "insideTopRight" : "insideTopLeft"
}

export function chartSummary(
  timeline: Timeline,
  candidates: readonly Candidate[]
): string {
  const rows = chartRows(timeline)
  if (rows.length === 0 || candidates.length === 0) {
    return "Minuto a minuto: aguardando os primeiros boletins."
  }
  const { leader, since } = leadSince(rows, candidates)
  const share = formatPercent(rows[rows.length - 1][seriesKey(leader.number)])
  const decided = decision(timeline)
  const outcome = decided
    ? `resultado matematicamente definido com ${oneDecimalPercent.format(decided.progress)} das seções`
    : "resultado ainda não definido"
  return `Minuto a minuto: ${leader.name} lidera com ${share} dos votos válidos desde ${oneDecimalPercent.format(since)} das seções; ${outcome}.`
}

export function labelOffsets(
  finals: ReadonlyArray<{ number: number; share: number }>,
  [low, high]: readonly [number, number],
  plotHeight: number,
  minGap = 14
): Map<number, number> {
  const pixels = (share: number) => ((high - share) / (high - low)) * plotHeight
  const ordered = [...finals].sort((a, b) => b.share - a.share)
  const offsets = new Map<number, number>()
  let previous = -Infinity
  for (const { number, share } of ordered) {
    const natural = pixels(share)
    const placed = Math.max(natural, previous + minGap)
    offsets.set(number, placed - natural)
    previous = placed
  }
  return offsets
}
