"use client"

import { CandidateRow } from "@/components/results/candidate-row"
import { SectionLabel } from "@/components/results/section-label"
import { useFlip } from "@/hooks/use-flip"
import { candidateColor } from "@/lib/candidate-colors"
import {
  finalistBadge,
  hasVerdict,
  isFinalist,
  type Results,
} from "@/lib/results"

export function CandidateList({ results }: { results: Results }) {
  const { candidates, verdict } = results
  const register = useFlip<HTMLLIElement>(candidates.map((c) => c.number))
  const decided = hasVerdict(results)

  return (
    <section aria-labelledby="candidates-title">
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
        <div id="candidates-title">
          <SectionLabel>Candidatos · % dos votos válidos</SectionLabel>
        </div>
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <span aria-hidden className="h-3 w-px bg-foreground/50" />
          50% · maioria absoluta
        </p>
      </div>
      <ol className="relative mt-2 divide-y border-y">
        {candidates.map((candidate) => {
          const finalist = isFinalist(results, candidate.number)
          return (
            <li key={candidate.number} ref={register(candidate.number)}>
              <CandidateRow
                candidate={candidate}
                color={candidateColor(candidates, candidate.number)}
                badge={finalist ? finalistBadge(verdict) : null}
                receded={decided && !finalist}
              />
            </li>
          )
        })}
      </ol>
    </section>
  )
}
