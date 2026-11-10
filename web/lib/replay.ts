import type { Results } from "@/lib/results"
import type { Timeline } from "@/lib/timeline"

export type ReplayPoint = { at: string; results: Results }
export type Replay = { year: number; round: number; points: ReplayPoint[] }
export type ReplaySpeed = 1 | 2 | 4

export const REPLAY_SPEEDS: readonly ReplaySpeed[] = [1, 2, 4]
export const BASE_DURATION_MS = 45_000
export const REPLAY_STATUS = { label: "Replay", tone: "warning" } as const

export function clampFraction(fraction: number): number {
  return Math.min(1, Math.max(0, fraction))
}

export function indexAt(count: number, fraction: number): number {
  if (count === 0) return 0
  return Math.min(count - 1, Math.floor(clampFraction(fraction) * count))
}

export function fractionOf(count: number, index: number): number {
  return count <= 1 ? 1 : index / (count - 1)
}

export function advance(
  fraction: number,
  elapsedMs: number,
  speed: ReplaySpeed
): number {
  return clampFraction(fraction + (elapsedMs * speed) / BASE_DURATION_MS)
}

export function timelineUpTo(timeline: Timeline, index: number): Timeline {
  const points = timeline.points.slice(0, index + 1)
  const last = points[points.length - 1]
  const decided = timeline.decided_at
  return {
    ...timeline,
    points,
    decided_at:
      decided && last && Date.parse(decided) <= Date.parse(last.at)
        ? decided
        : null,
  }
}
