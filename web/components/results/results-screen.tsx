"use client"

import { useCallback, useState } from "react"

import { ApiUnavailableNotice } from "@/components/results/api-unavailable-notice"
import { ResultsHeader } from "@/components/results/results-header"
import { ResultsSkeleton } from "@/components/results/results-skeleton"
import { RoundTabs } from "@/components/results/round-tabs"
import { NewCountDialog } from "@/components/results/new-count-dialog"
import { RoundView, type RoundReport } from "@/components/results/round-view"
import { RunBadge } from "@/components/results/run-badge"
import { SetupPendingCard } from "@/components/results/setup-pending-card"
import { ThemeToggle } from "@/components/theme-toggle"
import { Tabs, TabsContent } from "@/components/ui/tabs"
import { useCurrentRun } from "@/hooks/use-current-run"
import { useRounds } from "@/hooks/use-rounds"
import { useSelectedRound } from "@/hooks/use-selected-round"
import { LIVE_STATUS, sameReport } from "@/lib/connection"
import { REPLAY_STATUS } from "@/lib/replay"
import { findRound } from "@/lib/rounds"

const DEFAULT_YEAR = 2026
const DEFAULT_ROUND = 1
const INITIAL_REPORT: RoundReport = { ...LIVE_STATUS, year: null }

export function ResultsScreen() {
  const { status, rounds, refresh: refreshRounds } = useRounds()
  const { selected, select, follow } = useSelectedRound(rounds)
  const { current, refresh: refreshRun } = useCurrentRun()
  const [report, setReport] = useState(INITIAL_REPORT)
  const onReport = useCallback((next: RoundReport) => {
    setReport((previous) => (sameReport(previous, next) ? previous : next))
  }, [])
  const followActiveRun = useCallback(() => {
    refreshRounds()
    refreshRun()
    follow()
  }, [refreshRounds, refreshRun, follow])
  const run = current?.run ?? null
  const replaying = report.label === REPLAY_STATUS.label
  const liveStatus =
    selected?.status === "live" && !replaying ? report : LIVE_STATUS

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
          <div className="flex flex-wrap items-center justify-between gap-3">
            {run && <RunBadge run={run} />}
            {current?.runs_enabled && (
              <NewCountDialog onStarted={followActiveRun} />
            )}
            <RoundTabs
              rounds={rounds}
              liveStatus={liveStatus}
              selected={selected?.round ?? null}
              replaying={replaying}
            />
            <ThemeToggle />
          </div>
        </div>
        {status === "unavailable" && (
          <ApiUnavailableNotice hasData={rounds.length > 0} />
        )}
        {selected ? (
          <TabsContent value={String(selected.round)}>
            <RoundView
              key={`${selected.round}-${selected.status}-${run?.id}`}
              round={selected}
              hasFirstRound={findRound(rounds, 1) !== undefined}
              onReport={onReport}
              onRun={followActiveRun}
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
