import { CandidateList } from "@/components/results/candidate-list"
import { ProgressPanel } from "@/components/results/progress-panel"
import { VerdictBanner } from "@/components/results/verdict-banner"
import { VoteBreakdown } from "@/components/results/vote-breakdown"
import type { Results } from "@/lib/results"

export function ResultsBoard({ results }: { results: Results }) {
  return (
    <div className="space-y-10">
      <ProgressPanel progress={results.progress} />
      <VerdictBanner results={results} />
      <CandidateList results={results} />
      <VoteBreakdown results={results} />
    </div>
  )
}
