import { CandidateList } from "@/components/results/candidate-list"
import { ProgressPanel } from "@/components/results/progress-panel"
import { TimelineSection } from "@/components/results/timeline-section"
import { VerdictBanner } from "@/components/results/verdict-banner"
import { VoteBreakdown } from "@/components/results/vote-breakdown"
import type { Results } from "@/lib/results"
import { decision, type Timeline } from "@/lib/timeline"

export function ResultsBoard({
  results,
  timeline,
  palette,
}: {
  results: Results
  timeline: Timeline | null
  palette: readonly number[]
}) {
  return (
    <div className="space-y-10">
      <ProgressPanel progress={results.progress} />
      <VerdictBanner
        results={results}
        palette={palette}
        decision={decision(timeline)}
      />
      <div className="grid gap-10 lg:grid-cols-12 lg:gap-x-12">
        <div className="min-w-0 lg:order-2 lg:col-span-7">
          <TimelineSection
            timeline={timeline}
            candidates={results.candidates}
            palette={palette}
          />
        </div>
        <div className="min-w-0 lg:order-1 lg:col-span-5">
          <CandidateList results={results} palette={palette} />
        </div>
      </div>
      <VoteBreakdown results={results} />
    </div>
  )
}
