import type { Pipeline } from "@/lib/pipeline"

export function makePipeline(overrides: Partial<Pipeline> = {}): Pipeline {
  return {
    run: { id: 7, round: 1, seed: 205504 },
    stream_length: 4200,
    pending: 300,
    lag: 120,
    consumers: [
      { name: "demo-0-0", pending: 200, idle_ms: 300, active: true },
      { name: "demo-1-0", pending: 100, idle_ms: 42_000, active: false },
    ],
    rejected: 3,
    counted_sections: 3800,
    rate: 612.4,
    peak_rate: 1480,
    rates: [0, 400, 612.4],
    ...overrides,
  }
}
