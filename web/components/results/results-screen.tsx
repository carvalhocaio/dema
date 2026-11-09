"use client"

import { ApiUnavailableNotice } from "@/components/results/api-unavailable-notice"
import { ResultsBoard } from "@/components/results/results-board"
import { ResultsHeader } from "@/components/results/results-header"
import { ResultsSkeleton } from "@/components/results/results-skeleton"
import { SetupPendingCard } from "@/components/results/setup-pending-card"
import { useResults, type ResultsState } from "@/hooks/use-results"
import { connectionStatus } from "@/lib/connection"

const DEFAULT_YEAR = 2026
const DEFAULT_ROUND = 1

function ResultsBody({
  results,
  setup,
}: Pick<ResultsState, "results" | "setup">) {
  if (results) return <ResultsBoard results={results} />
  if (setup === "pending") return <SetupPendingCard />
  return <ResultsSkeleton />
}

export function ResultsScreen() {
  const state = useResults()
  const { results, connection, setup } = state

  return (
    <main className="mx-auto w-full max-w-[960px] space-y-10 px-4 py-8 tabular-nums sm:px-6 sm:py-12">
      <ResultsHeader
        year={results?.year ?? DEFAULT_YEAR}
        round={results?.round ?? DEFAULT_ROUND}
        status={connectionStatus(connection, setup)}
      />
      {connection === "unavailable" && (
        <ApiUnavailableNotice hasData={results !== null} />
      )}
      <ResultsBody results={results} setup={setup} />
    </main>
  )
}
