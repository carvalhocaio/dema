import { CandidateMarker } from "@/components/results/candidate-marker"
import { candidateColor } from "@/lib/candidate-colors"
import { formatPercent, type Candidate } from "@/lib/results"
import { formatClock, seriesKey, type ChartRow } from "@/lib/timeline"
import { cn } from "@/lib/utils"

type EndLabelProps = {
  x?: number | string
  y?: number | string
  index?: number
  value?: number | string
  lastIndex: number
  color: string
  offset: number
}

export function EndLabel({
  x,
  y,
  index,
  value,
  lastIndex,
  color,
  offset,
}: EndLabelProps) {
  if (index !== lastIndex) return null
  return (
    <text
      x={Number(x) + 6}
      y={Number(y) + offset}
      dy={4}
      fill={color}
      fontSize={12}
      fontWeight={600}
      className="tabular-nums"
    >
      {formatPercent(Number(value))}
    </text>
  )
}

type TooltipProps = {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: ChartRow }>
  candidates: readonly Candidate[]
  palette: readonly number[]
}

export function TimelineTooltip({
  active,
  payload,
  candidates,
  palette,
}: TooltipProps) {
  const row = payload?.[0]?.payload
  if (!active || !row) return null
  const ranked = [...candidates].sort(
    (a, b) => row[seriesKey(b.number)] - row[seriesKey(a.number)]
  )
  return (
    <div className="min-w-44 rounded-md border bg-background px-3 py-2 text-xs tabular-nums shadow-sm">
      <p className="font-medium">
        {formatClock(row.at)} · {formatPercent(row.progress)} das seções
      </p>
      <ul className="mt-1.5 space-y-1">
        {ranked.map((candidate) => (
          <li key={candidate.number} className="flex items-center gap-2">
            <CandidateMarker
              color={candidateColor(palette, candidate.number)}
            />
            <span className="flex-1 text-muted-foreground">
              {candidate.name}
            </span>
            <span className="font-medium">
              {formatPercent(row[seriesKey(candidate.number)])}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function TimelineLegend({
  candidates,
  emphasized,
  palette,
}: {
  candidates: readonly Candidate[]
  emphasized: ReadonlySet<number>
  palette: readonly number[]
}) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
      {candidates.map((candidate) => {
        const strong = emphasized.has(candidate.number)
        return (
          <li
            key={candidate.number}
            className={cn(
              "flex items-center gap-1.5",
              strong ? "font-medium" : "text-muted-foreground"
            )}
          >
            <span
              aria-hidden
              className={cn(
                "inline-block w-4 rounded-full",
                strong ? "h-0.5" : "h-px"
              )}
              style={{
                backgroundColor: candidateColor(palette, candidate.number),
              }}
            />
            {candidate.name} ({candidate.number})
          </li>
        )
      })}
    </ul>
  )
}
