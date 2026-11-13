import { describe, expect, it } from "vitest"

import {
  activeConsumers,
  formatIdle,
  formatRate,
  sparklinePoints,
} from "@/lib/pipeline"
import { makePipeline } from "@/test/pipeline"

describe("pipeline presentation", () => {
  it("formats rates with one decimal in pt-BR", () => {
    expect(formatRate(1480)).toBe("1.480,0")
    expect(formatRate(612.44)).toBe("612,4")
  })

  it("describes how long a worker has been idle", () => {
    expect(formatIdle(300)).toBe("agora")
    expect(formatIdle(42_500)).toBe("42 s")
    expect(formatIdle(185_000)).toBe("3 min")
  })

  it("counts the active workers", () => {
    expect(activeConsumers(makePipeline())).toBe(1)
  })

  it("draws nothing until there are two samples", () => {
    expect(sparklinePoints([], 100, 10)).toBe("")
    expect(sparklinePoints([5], 100, 10)).toBe("")
  })

  it("scales the samples to the box with the peak on top", () => {
    expect(sparklinePoints([0, 50, 100], 100, 10)).toBe("0,10 50,5 100,0")
  })

  it("keeps an idle pipeline on the baseline", () => {
    expect(sparklinePoints([0, 0, 0], 90, 30)).toBe("0,30 45,30 90,30")
  })
})
