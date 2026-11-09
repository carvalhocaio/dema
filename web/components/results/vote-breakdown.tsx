import { SectionLabel } from "@/components/results/section-label"
import {
  formatInteger,
  formatPercent,
  voteBreakdown,
  type Results,
} from "@/lib/results"

export function VoteBreakdown({ results }: { results: Results }) {
  return (
    <section aria-labelledby="breakdown-title" className="space-y-3">
      <div id="breakdown-title">
        <SectionLabel>Votos</SectionLabel>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-5">
        {voteBreakdown(results).map((item) => (
          <div key={item.label} className="min-w-0">
            <dt className="text-sm text-muted-foreground">{item.label}</dt>
            <dd className="mt-1 text-lg font-semibold">
              {formatInteger(item.value)}
            </dd>
            <dd className="text-sm text-muted-foreground">
              {formatPercent(item.share)}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
