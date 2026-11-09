import { CandidateMarker } from "@/components/results/candidate-marker"
import { candidateColor } from "@/lib/candidate-colors"
import {
  finalistCandidates,
  formatPercent,
  verdictLabel,
  type Results,
} from "@/lib/results"
import { formatElapsed, type Decision } from "@/lib/timeline"

export function VerdictBanner({
  results,
  palette,
  decision,
}: {
  results: Results
  palette: readonly number[]
  decision: Decision | null
}) {
  const label = verdictLabel(results)
  if (!label) return null
  const finalists = finalistCandidates(results)

  return (
    <section
      aria-live="polite"
      className="rounded-lg border border-foreground/15 bg-card px-5 py-4"
    >
      <div className="flex items-center gap-3">
        <div className="flex gap-1">
          {finalists.map((candidate) => (
            <CandidateMarker
              key={candidate.number}
              color={candidateColor(palette, candidate.number)}
            />
          ))}
        </div>
        <p className="text-lg font-semibold tracking-tight sm:text-xl">
          {label}
        </p>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        {decision
          ? `Matematicamente definido com ${formatPercent(decision.progress)} das seções totalizadas, após ${formatElapsed(decision.elapsed)} de apuração.`
          : `Matematicamente definido com ${formatPercent(results.progress.ratio)} das seções totalizadas.`}
      </p>
    </section>
  )
}
