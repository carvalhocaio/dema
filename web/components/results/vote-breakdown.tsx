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
      <dl className="divide-y border-y md:grid md:grid-cols-5 md:gap-x-6 md:divide-y-0 md:border-y-0">
        {voteBreakdown(results).map((item) => (
          <div
            key={item.label}
            className="grid min-w-0 grid-cols-[1fr_auto] items-baseline gap-x-4 py-3 md:grid-cols-1 md:py-0"
          >
            <dt className="row-span-2 text-sm text-muted-foreground md:row-span-1">
              {item.label}
            </dt>
            <dd className="text-right text-lg font-semibold md:mt-1 md:text-left">
              {formatInteger(item.value)}
            </dd>
            <dd className="text-right text-sm text-muted-foreground md:text-left">
              <span className="font-medium text-foreground/80">
                {formatPercent(item.share)}
              </span>{" "}
              <span className="text-xs md:block">{item.basis}</span>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
