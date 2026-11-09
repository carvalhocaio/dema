import { CandidateList } from "@/components/results/candidate-list"
import { ProgressPanel } from "@/components/results/progress-panel"
import { TimelineSection } from "@/components/results/timeline-section"
import { VerdictBanner } from "@/components/results/verdict-banner"
import { VoteBreakdown } from "@/components/results/vote-breakdown"
import type { Results } from "@/lib/results"
import { decisionPoint, type Timeline } from "@/lib/timeline"

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
        decision={decisionPoint(timeline)}
      />
      <TimelineSection
        timeline={timeline}
        candidates={results.candidates}
        palette={palette}
      />
      <CandidateList results={results} palette={palette} />
      <VoteBreakdown results={results} />
    </div>
  )
}
