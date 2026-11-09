import { describe, expect, it } from "vitest"

import {
  chartRows,
  chartSummary,
  clockTicks,
  decisionPoint,
  emphasizedNumbers,
  formatClock,
  formatPercentTick,
  labelOffsets,
  leadSince,
  seriesKey,
  yDomain,
  yTicks,
} from "@/lib/timeline"
import { makeResults } from "@/test/fixtures"
import { makeTimeline, point } from "@/test/timeline"

const CANDIDATES = makeResults().candidates
const MINUTE = 60_000
const START = Date.parse("2026-10-04T20:00:00Z")

describe("formatPercentTick", () => {
  it("shows whole percentages on the axis", () => {
    expect(formatPercentTick(0.45)).toBe("45%")
  })
})

describe("formatClock", () => {
  it("shows Brasília time", () => {
    expect(formatClock(START)).toBe("17:00")
    expect(formatClock(Date.parse("2026-10-05T03:05:00Z"))).toBe("00:05")
  })
})

describe("chartRows", () => {
  it("turns points into rows keyed by series", () => {
    const [first] = chartRows(makeTimeline())

    expect(first).toEqual({
      at: START,
      progress: 0.1,
      c27: 0.4,
      c99: 0.5,
      c31: 0.1,
    })
    expect(seriesKey(27)).toBe("c27")
  })
})

describe("yDomain and yTicks", () => {
  it("pads the shares to 5-point steps and always shows the majority line", () => {
    const rows = chartRows(makeTimeline())

    expect(yDomain(rows, [27, 99])).toEqual([0.35, 0.55])
    expect(yTicks([0.35, 0.55])).toEqual([0.35, 0.4, 0.45, 0.5, 0.55])
  })

  it("stays within 0 and 100% and thins out wide ranges", () => {
    const rows = chartRows(makeTimeline())

    expect(yDomain(rows, [27, 99, 31])).toEqual([0.05, 0.55])
    expect(
      yDomain(
        chartRows(
          makeTimeline({
            points: [point("2026-10-04T20:00:00Z", { "27": 0.99, "99": 0.0 })],
          })
        ),
        [27, 99]
      )
    ).toEqual([0, 1])
    expect(yTicks([0.05, 0.55])).toEqual([0.1, 0.2, 0.3, 0.4, 0.5])
  })
})

describe("clockTicks", () => {
  it("picks the finest step that keeps the axis readable", () => {
    expect(clockTicks(START, START + 60 * MINUTE)).toEqual([
      START,
      START + 15 * MINUTE,
      START + 30 * MINUTE,
      START + 45 * MINUTE,
      START + 60 * MINUTE,
    ])
    expect(clockTicks(START + MINUTE, START + 9 * 60 * MINUTE)).toHaveLength(4)
  })

  it("caps very long counts at the widest step", () => {
    const ticks = clockTicks(START, START + 72 * 60 * MINUTE)

    expect(ticks[1] - ticks[0]).toBe(360 * MINUTE)
  })
})

describe("emphasis and leadership", () => {
  it("stresses the top two in the first round and everyone in the runoff", () => {
    expect(emphasizedNumbers(1, CANDIDATES)).toEqual([27, 99])
    expect(emphasizedNumbers(2, CANDIDATES)).toEqual([27, 99, 31])
  })

  it("finds when the current leader took the lead", () => {
    const rows = chartRows(makeTimeline())

    const { leader, since } = leadSince(rows, CANDIDATES)

    expect(leader.number).toBe(27)
    expect(since).toBe(START + 30 * MINUTE)
  })

  it("dates a lead held from the first minute to that minute", () => {
    const rows = chartRows(makeTimeline()).slice(0, 1)

    expect(leadSince(rows, CANDIDATES)).toMatchObject({ since: START })
  })
})

describe("chartSummary", () => {
  it("describes the leader, since when and the decision time", () => {
    expect(chartSummary(makeTimeline(), CANDIDATES)).toBe(
      "Minuto a minuto: Keons lidera com 50,00% dos votos válidos desde 17:30; resultado matematicamente definido às 17:30."
    )
  })

  it("says when the result is still open", () => {
    const summary = chartSummary(makeTimeline({ decided_at: null }), CANDIDATES)

    expect(summary).toMatch(/resultado ainda não definido\.$/)
  })

  it("waits for the first ballots", () => {
    const waiting = "Minuto a minuto: aguardando os primeiros boletins."

    expect(chartSummary(makeTimeline({ points: [] }), CANDIDATES)).toBe(waiting)
    expect(chartSummary(makeTimeline(), [])).toBe(waiting)
  })
})

describe("labelOffsets", () => {
  it("pushes colliding end labels apart and leaves distant ones alone", () => {
    const offsets = labelOffsets(
      [
        { number: 99, share: 0.49 },
        { number: 27, share: 0.5 },
        { number: 31, share: 0.1 },
      ],
      [0, 1],
      200
    )

    expect(offsets.get(27)).toBe(0)
    expect(offsets.get(99)).toBeCloseTo(12)
    expect(offsets.get(31)).toBe(0)
  })
})

describe("decisionPoint", () => {
  it("returns the point where the verdict was secured", () => {
    expect(decisionPoint(makeTimeline())?.progress).toBe(0.6)
  })

  it("is empty without a timeline, a decision or a matching point", () => {
    expect(decisionPoint(null)).toBeNull()
    expect(decisionPoint(makeTimeline({ decided_at: null }))).toBeNull()
    expect(
      decisionPoint(makeTimeline({ decided_at: "2026-10-04T23:00:00Z" }))
    ).toBeNull()
  })
})
