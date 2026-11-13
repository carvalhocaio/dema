"use client"

import { useEffect } from "react"

import { ReplayControls } from "@/components/results/replay-controls"
import { ResultsBoard } from "@/components/results/results-board"
import { ResultsSkeleton } from "@/components/results/results-skeleton"
import { SetupPendingCard } from "@/components/results/setup-pending-card"
import { usePalette } from "@/hooks/use-palette"
import { useReplay, type ReplayClock } from "@/hooks/use-replay"
import { useReplayData } from "@/hooks/use-replay-data"
import { useRoundResults } from "@/hooks/use-round-results"
import { useStates } from "@/hooks/use-states"
import { useTimeline } from "@/hooks/use-timeline"
import { connectionStatus, type StatusReport } from "@/lib/connection"
import { indexAt, REPLAY_STATUS, timelineUpTo } from "@/lib/replay"
import type { Pipeline } from "@/lib/pipeline"
import type { Round } from "@/lib/rounds"
import type { RunRef } from "@/lib/runs"

export type RoundReport = StatusReport

export function RoundView({
  round,
  hasFirstRound,
  onReport,
  onRun,
  onPipeline,
  replayClock,
}: {
  round: Round
  hasFirstRound: boolean
  onReport: (report: RoundReport) => void
  onRun: (run: RunRef) => void
  onPipeline?: (pipeline: Pipeline) => void
  replayClock?: ReplayClock
}) {
  const live = useRoundResults(
    round.round,
    round.status === "live",
    onRun,
    onPipeline
  )
  const timeline = useTimeline(
    round.round,
    live.results?.progress.counted_sections ?? null
  )
  const states = useStates(
    round.round,
    live.results?.progress.counted_sections ?? null
  )
  const palette = usePalette(hasFirstRound, live.results)
  const [replay, controls] = useReplay(replayClock)
  const replaying = replay.status !== "idle"
  const data = useReplayData(round.round, replaying)
  const frame =
    replaying && data.status === "ready" && timeline
      ? indexAt(data.replay.points.length, replay.fraction)
      : null
  const results =
    frame !== null && data.status === "ready"
      ? data.replay.points[frame].results
      : live.results
  const year = results?.year ?? null
  const status = replaying
    ? REPLAY_STATUS
    : connectionStatus(live.connection, live.setup)

  useEffect(() => {
    onReport({ ...status, year })
  }, [onReport, status, year])

  if (!results) {
    if (live.setup === "pending") return <SetupPendingCard />
    return <ResultsSkeleton />
  }
  return (
    <div className="space-y-6">
      {live.results?.progress.is_complete && (
        <ReplayControls
          state={replay}
          controls={controls}
          loading={data.status === "loading"}
        />
      )}
      <ResultsBoard
        results={results}
        timeline={
          frame !== null && timeline ? timelineUpTo(timeline, frame) : timeline
        }
        states={replaying ? null : states}
        palette={palette}
      />
    </div>
  )
}
