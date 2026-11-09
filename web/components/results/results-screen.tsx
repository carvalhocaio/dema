"use client"

import { useCallback, useState } from "react"

import { ApiUnavailableNotice } from "@/components/results/api-unavailable-notice"
import { ResultsHeader } from "@/components/results/results-header"
import { ResultsSkeleton } from "@/components/results/results-skeleton"
import { RoundTabs } from "@/components/results/round-tabs"
import { RoundView, type RoundReport } from "@/components/results/round-view"
import { SetupPendingCard } from "@/components/results/setup-pending-card"
import { ThemeToggle } from "@/components/theme-toggle"
import { Tabs, TabsContent } from "@/components/ui/tabs"
import { useRounds } from "@/hooks/use-rounds"
import { useSelectedRound } from "@/hooks/use-selected-round"
import { LIVE_STATUS, sameReport } from "@/lib/connection"
import { findRound } from "@/lib/rounds"

const DEFAULT_YEAR = 2026
const DEFAULT_ROUND = 1
const INITIAL_REPORT: RoundReport = { ...LIVE_STATUS, year: null }

export function ResultsScreen() {
  const { status, rounds } = useRounds()
  const [selected, select] = useSelectedRound(rounds)
  const [report, setReport] = useState(INITIAL_REPORT)
  const onReport = useCallback((next: RoundReport) => {
    setReport((previous) => (sameReport(previous, next) ? previous : next))
  }, [])
  const liveStatus = selected?.status === "live" ? report : LIVE_STATUS

  return (
    <main className="mx-auto w-full max-w-screen-2xl px-4 py-8 tabular-nums sm:px-6 sm:py-12 lg:px-10">
      <Tabs
        value={selected ? String(selected.round) : ""}
        onValueChange={(value) => select(Number(value))}
        className="gap-8"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <ResultsHeader
            year={report.year ?? DEFAULT_YEAR}
            round={selected?.round ?? DEFAULT_ROUND}
          />
          <div className="flex items-center justify-between gap-3">
            <RoundTabs rounds={rounds} liveStatus={liveStatus} />
            <ThemeToggle />
          </div>
        </div>
        {status === "unavailable" && (
          <ApiUnavailableNotice hasData={rounds.length > 0} />
        )}
        {selected ? (
          <TabsContent value={String(selected.round)}>
            <RoundView
              key={`${selected.round}-${selected.status}`}
              round={selected}
              hasFirstRound={findRound(rounds, 1) !== undefined}
              onReport={onReport}
            />
          </TabsContent>
        ) : status === "ready" ? (
          <SetupPendingCard />
        ) : (
          <ResultsSkeleton />
        )}
      </Tabs>
    </main>
  )
}
