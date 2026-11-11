import { CandidateMarker } from "@/components/results/candidate-marker"
import { candidateColor } from "@/lib/candidate-colors"
import { formatPercent, type Candidate } from "@/lib/results"
import { byRegion, REGION_LABELS, type States } from "@/lib/states"

export function StateList({
  states,
  candidates,
  palette,
}: {
  states: States
  candidates: readonly Candidate[]
  palette: readonly number[]
}) {
  const names = new Map(candidates.map((c) => [c.number, c.name]))
  return (
    <dl className="grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
      {[...byRegion(states.states)].map(([region, items]) => (
        <div key={region}>
          <dt className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
            {REGION_LABELS[region]}
          </dt>
          <dd className="mt-1 divide-y">
            {items.map((state) => (
              <div
                key={state.state}
                className="flex items-center gap-2 py-1 tabular-nums"
              >
                <span className="w-7 font-mono font-semibold">
                  {state.state}
                </span>
                {state.leader != null ? (
                  <>
                    <CandidateMarker
                      color={candidateColor(palette, state.leader)}
                    />
                    <span className="flex-1 truncate">
                      {names.get(state.leader)}
                    </span>
                  </>
                ) : (
                  <span className="flex-1 text-muted-foreground">—</span>
                )}
                <span className="text-muted-foreground">
                  {formatPercent(state.progress)}
                </span>
              </div>
            ))}
          </dd>
        </div>
      ))}
    </dl>
  )
}
