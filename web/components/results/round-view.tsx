"use client"

import { useEffect } from "react"

import { ResultsBoard } from "@/components/results/results-board"
import { ResultsSkeleton } from "@/components/results/results-skeleton"
import { SetupPendingCard } from "@/components/results/setup-pending-card"
import { usePalette } from "@/hooks/use-palette"
import { useRoundResults } from "@/hooks/use-round-results"
import { useTimeline } from "@/hooks/use-timeline"
import { connectionStatus, type StatusReport } from "@/lib/connection"
import type { Round } from "@/lib/rounds"

export type RoundReport = StatusReport

export function RoundView({
  round,
  hasFirstRound,
  onReport,
}: {
  round: Round
  hasFirstRound: boolean
  onReport: (report: RoundReport) => void
}) {
  const { results, connection, setup } = useRoundResults(
    round.round,
    round.status === "live"
  )
  const timeline = useTimeline(
    round.round,
    results?.progress.counted_sections ?? null
  )
  const palette = usePalette(hasFirstRound, results)
  const year = results?.year ?? null

  useEffect(() => {
    onReport({ ...connectionStatus(connection, setup), year })
  }, [onReport, connection, setup, year])

  if (results) {
    return (
      <ResultsBoard results={results} timeline={timeline} palette={palette} />
    )
  }
  if (setup === "pending") return <SetupPendingCard />
  return <ResultsSkeleton />
}
