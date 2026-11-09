import { describe, expect, it } from "vitest"

import {
  chartRows,
  chartSummary,
  decision,
  decisionLabelPosition,
  emphasizedNumbers,
  formatElapsed,
  formatPercentTick,
  labelOffsets,
  leadSince,
  PROGRESS_TICKS,
  seriesKey,
  yDomain,
  yTicks,
} from "@/lib/timeline"
import { makeResults } from "@/test/fixtures"
import { makeTimeline, point } from "@/test/timeline"

const CANDIDATES = makeResults().candidates
const MINUTE = 60_000

describe("formatPercentTick", () => {
  it("shows whole percentages on both axes", () => {
    expect(formatPercentTick(0.45)).toBe("45%")
    expect(PROGRESS_TICKS.map(formatPercentTick)).toEqual([
      "0%",
      "25%",
      "50%",
      "75%",
      "100%",
    ])
  })
})

describe("formatElapsed", () => {
  it("counts minutes, then hours and minutes", () => {
    expect(formatElapsed(0)).toBe("0 min")
    expect(formatElapsed(12 * MINUTE)).toBe("12 min")
    expect(formatElapsed(59.6 * MINUTE)).toBe("1h00")
    expect(formatElapsed(72 * MINUTE)).toBe("1h12")
    expect(formatElapsed(141 * MINUTE)).toBe("2h21")
  })
})

describe("chartRows", () => {
  it("keys shares by series and measures time since the first ballots", () => {
    const rows = chartRows(makeTimeline())

    expect(rows[0]).toEqual({
      progress: 0.1,
      elapsed: 0,
      c27: 0.4,
      c99: 0.5,
      c31: 0.1,
    })
    expect(rows.map((row) => row.elapsed)).toEqual([
      0,
      30 * MINUTE,
      60 * MINUTE,
    ])
    expect(seriesKey(27)).toBe("c27")
  })

  it("is empty before any point", () => {
    expect(chartRows(makeTimeline({ points: [] }))).toEqual([])
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
    const landslide = makeTimeline({
      points: [point("2026-10-04T20:00:00Z", { "27": 0.99, "99": 0.0 })],
    })

    expect(yDomain(rows, [27, 99, 31])).toEqual([0.05, 0.55])
    expect(yDomain(chartRows(landslide), [27, 99])).toEqual([0, 1])
    expect(yTicks([0.05, 0.55])).toEqual([0.1, 0.2, 0.3, 0.4, 0.5])
  })
})

describe("emphasis and leadership", () => {
  it("stresses the top two in the first round and everyone in the runoff", () => {
    expect(emphasizedNumbers(1, CANDIDATES)).toEqual([27, 99])
    expect(emphasizedNumbers(2, CANDIDATES)).toEqual([27, 99, 31])
  })

  it("finds the share of sections when the current leader took the lead", () => {
    const { leader, since } = leadSince(chartRows(makeTimeline()), CANDIDATES)

    expect(leader.number).toBe(27)
    expect(since).toBe(0.6)
  })

  it("dates a lead held from the first minute to that minute", () => {
    const rows = chartRows(makeTimeline()).slice(0, 1)

    expect(leadSince(rows, CANDIDATES)).toMatchObject({ since: 0.1 })
  })
})

describe("decision", () => {
  it("locates the minute the verdict was secured", () => {
    expect(decision(makeTimeline())).toEqual({
      progress: 0.6,
      elapsed: 30 * MINUTE,
    })
  })

  it("is empty without a timeline, a decision or a matching point", () => {
    expect(decision(null)).toBeNull()
    expect(decision(makeTimeline({ decided_at: null }))).toBeNull()
    expect(
      decision(makeTimeline({ decided_at: "2026-10-04T23:00:00Z" }))
    ).toBeNull()
  })

  it("keeps the label clear of the end labels late in the count", () => {
    expect(decisionLabelPosition(0.6)).toBe("insideTopLeft")
    expect(decisionLabelPosition(0.95)).toBe("insideTopRight")
  })
})

describe("chartSummary", () => {
  it("describes the leader, since when and the decision", () => {
    expect(chartSummary(makeTimeline(), CANDIDATES)).toBe(
      "Minuto a minuto: Keons lidera com 50,00% dos votos válidos desde 60% das seções; resultado matematicamente definido com 60% das seções."
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
