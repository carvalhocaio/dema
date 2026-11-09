import { CandidateMarker } from "@/components/results/candidate-marker"
import { candidateColor } from "@/lib/candidate-colors"
import {
  finalistCandidates,
  formatPercent,
  verdictLabel,
  type Results,
} from "@/lib/results"

export function VerdictBanner({ results }: { results: Results }) {
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
              color={candidateColor(results.candidates, candidate.number)}
            />
          ))}
        </div>
        <p className="text-lg font-semibold tracking-tight sm:text-xl">
          {label}
        </p>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Resultado matematicamente definido com{" "}
        {formatPercent(results.progress.ratio)} das seções totalizadas.
      </p>
    </section>
  )
}
