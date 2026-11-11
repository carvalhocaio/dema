import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { candidateColor } from "@/lib/candidate-colors"
import { formatPercent, type Candidate } from "@/lib/results"
import { formatPercentTick } from "@/lib/timeline"
import {
  GRID_COLUMNS,
  GRID_ROWS,
  statesSummary,
  TILES,
  tileIntensity,
  topTwo,
  type StateResult,
  type States,
} from "@/lib/states"

export function StateMap({
  states,
  candidates,
  palette,
}: {
  states: States
  candidates: readonly Candidate[]
  palette: readonly number[]
}) {
  const byState = new Map(states.states.map((state) => [state.state, state]))
  const names = new Map(candidates.map((c) => [c.number, c.name]))

  return (
    <div
      role="img"
      aria-label={statesSummary(states, candidates)}
      className="grid gap-1"
      style={{
        gridTemplateColumns: `repeat(${GRID_COLUMNS}, minmax(0, 1fr))`,
        gridTemplateRows: `repeat(${GRID_ROWS}, minmax(0, 1fr))`,
      }}
    >
      {TILES.map((tile) => {
        const result = byState.get(tile.state)
        return (
          <StateTile
            key={tile.state}
            state={tile.state}
            result={result}
            column={tile.column}
            row={tile.row}
            color={
              result?.leader != null
                ? candidateColor(palette, result.leader)
                : "var(--muted)"
            }
            names={names}
          />
        )
      })}
    </div>
  )
}

function StateTile({
  state,
  result,
  column,
  row,
  color,
  names,
}: {
  state: string
  result: StateResult | undefined
  column: number
  row: number
  color: string
  names: ReadonlyMap<number, string>
}) {
  const counted = result !== undefined && result.counted_sections > 0
  const intensity = counted ? tileIntensity(result.progress) : 0
  const label = counted ? formatPercentTick(result.progress) : "—"
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          tabIndex={0}
          className="relative flex aspect-square flex-col items-center justify-center rounded-sm border border-border/60 text-[11px] leading-tight tabular-nums select-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden"
          style={{
            gridColumn: column,
            gridRow: row,
            backgroundColor: `color-mix(in oklab, ${color} ${Math.round(
              100 * intensity
            )}%, var(--muted))`,
          }}
        >
          <span className="font-semibold">{state}</span>
          <span className="text-[10px] opacity-80">{label}</span>
        </div>
      </TooltipTrigger>
      <TooltipContent className="tabular-nums">
        <StateTooltip state={state} result={result} names={names} />
      </TooltipContent>
    </Tooltip>
  )
}

function StateTooltip({
  state,
  result,
  names,
}: {
  state: string
  result: StateResult | undefined
  names: ReadonlyMap<number, string>
}) {
  if (!result) return <span>{state}: sem seções</span>
  const leaders = topTwo(result)
  return (
    <div className="space-y-0.5">
      <p className="font-medium">
        {state} · {formatPercent(result.progress)} apurado
      </p>
      {leaders.map((candidate) => (
        <p key={candidate.number}>
          {names.get(candidate.number) ?? candidate.number}{" "}
          {formatPercent(candidate.share)}
        </p>
      ))}
    </div>
  )
}
