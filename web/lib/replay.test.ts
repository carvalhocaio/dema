import { describe, expect, it } from "vitest"

import {
  advance,
  BASE_DURATION_MS,
  clampFraction,
  fractionOf,
  indexAt,
  timelineUpTo,
} from "@/lib/replay"
import { makeTimeline } from "@/test/timeline"

describe("replay position", () => {
  it("clamps fractions and maps them to point indexes", () => {
    expect(clampFraction(-1)).toBe(0)
    expect(clampFraction(2)).toBe(1)
    expect(indexAt(0, 0.5)).toBe(0)
    expect(indexAt(3, 0)).toBe(0)
    expect(indexAt(3, 0.34)).toBe(1)
    expect(indexAt(3, 1)).toBe(2)
    expect(fractionOf(3, 1)).toBe(0.5)
    expect(fractionOf(1, 0)).toBe(1)
  })

  it("advances at the chosen speed over the base duration", () => {
    expect(advance(0, BASE_DURATION_MS / 2, 1)).toBe(0.5)
    expect(advance(0, BASE_DURATION_MS / 2, 2)).toBe(1)
    expect(advance(0.9, BASE_DURATION_MS, 4)).toBe(1)
  })
})

describe("timelineUpTo", () => {
  it("keeps only the points already replayed and the decision once reached", () => {
    const timeline = makeTimeline()

    expect(timelineUpTo(timeline, 0)).toEqual({
      ...timeline,
      points: timeline.points.slice(0, 1),
      lead_changes: [],
      decided_at: null,
    })
    expect(timelineUpTo(timeline, 1).decided_at).toBe(timeline.decided_at)
    expect(timelineUpTo(timeline, 2).points).toHaveLength(3)
  })

  it("has no decision for an undecided or empty timeline", () => {
    expect(
      timelineUpTo(makeTimeline({ decided_at: null }), 2).decided_at
    ).toBeNull()
    expect(timelineUpTo(makeTimeline({ points: [] }), 0).decided_at).toBeNull()
  })
})
