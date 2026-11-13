import type { RunRef } from "@/lib/runs"

export type Consumer = {
  name: string
  pending: number
  idle_ms: number
  active: boolean
}

export type Pipeline = {
  run: RunRef
  stream_length: number
  pending: number
  lag: number | null
  consumers: Consumer[]
  rejected: number
  counted_sections: number
  rate: number
  peak_rate: number
  rates: number[]
}

const LOCALE = "pt-BR"
const SECOND_MS = 1_000
const MINUTE_MS = 60 * SECOND_MS

const rateFormat = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

export function formatRate(rate: number): string {
  return rateFormat.format(rate)
}

export function formatIdle(ms: number): string {
  if (ms < SECOND_MS) return "agora"
  if (ms < MINUTE_MS) return `${Math.floor(ms / SECOND_MS)} s`
  return `${Math.floor(ms / MINUTE_MS)} min`
}

export function activeConsumers(pipeline: Pipeline): number {
  return pipeline.consumers.filter((consumer) => consumer.active).length
}

export function sparklinePoints(
  rates: readonly number[],
  width: number,
  height: number
): string {
  if (rates.length < 2) return ""
  const top = Math.max(...rates, 1)
  const step = width / (rates.length - 1)
  return rates
    .map((rate, index) => {
      const x = index * step
      const y = height - (rate / top) * height
      return `${round(x)},${round(y)}`
    })
    .join(" ")
}

function round(value: number): number {
  return Math.round(value * 100) / 100
}
