import type { Timeline, TimelinePoint } from "@/lib/timeline"

export function point(
  at: string,
  shares: Record<string, number>,
  progress = 0.5,
  verdict: TimelinePoint["verdict"] = "undecided"
): TimelinePoint {
  return { at, progress, shares, verdict }
}

export function makeTimeline(overrides: Partial<Timeline> = {}): Timeline {
  return {
    year: 2026,
    round: 1,
    points: [
      point("2026-10-04T20:00:00Z", { "27": 0.4, "99": 0.5, "31": 0.1 }, 0.1),
      point("2026-10-04T20:30:00Z", { "27": 0.48, "99": 0.42, "31": 0.1 }, 0.6),
      point(
        "2026-10-04T21:00:00Z",
        { "27": 0.5, "99": 0.4, "31": 0.1 },
        1,
        "runoff"
      ),
    ],
    decided_at: "2026-10-04T20:30:00Z",
    lead_changes: ["2026-10-04T20:30:00Z"],
    ...overrides,
  }
}
