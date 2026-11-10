import type { Replay } from "@/lib/replay"
import { makeResults } from "@/test/fixtures"
import { makeTimeline } from "@/test/timeline"

export function makeReplay(overrides: Partial<Replay> = {}): Replay {
  const timeline = makeTimeline()
  return {
    year: 2026,
    round: 1,
    points: timeline.points.map((point, index) => ({
      at: point.at,
      results: makeResults({
        progress: { ...makeResults().progress, ratio: point.progress },
        verdict: point.verdict,
        finalists: point.verdict === "runoff" ? [27, 99] : [],
        candidates: makeResults().candidates.map((candidate) => ({
          ...candidate,
          share: point.shares[String(candidate.number)],
          votes: 100 * (index + 1),
        })),
      }),
    })),
    ...overrides,
  }
}
