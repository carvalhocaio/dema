"use client"

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts"

import {
  EndLabel,
  TimelineLegend,
  TimelineTooltip,
} from "@/components/results/timeline-parts"
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart"
import { DESKTOP_QUERY, useMediaQuery } from "@/hooks/use-media-query"
import { candidateColor } from "@/lib/candidate-colors"
import type { Candidate } from "@/lib/results"
import {
  chartRows,
  chartSummary,
  decision,
  decisionLabelPosition,
  emphasizedNumbers,
  formatPercentTick,
  labelOffsets,
  MAJORITY,
  PROGRESS_TICKS,
  seriesKey,
  yDomain,
  yTicks,
  type Timeline,
} from "@/lib/timeline"

const MOBILE_HEIGHT = 288
const DESKTOP_HEIGHT = 420
const MARGIN = { top: 12, right: 60, bottom: 4, left: 4 }
const X_AXIS_HEIGHT = 24

export function chartHeight(desktop: boolean): number {
  return desktop ? DESKTOP_HEIGHT : MOBILE_HEIGHT
}

function plotHeight(height: number): number {
  return height - MARGIN.top - MARGIN.bottom - X_AXIS_HEIGHT
}

type Props = {
  timeline: Timeline
  candidates: readonly Candidate[]
  palette: readonly number[]
}

export function TimelineChart({ timeline, candidates, palette }: Props) {
  const height = chartHeight(useMediaQuery(DESKTOP_QUERY))
  const rows = chartRows(timeline)
  const numbers = candidates.map((candidate) => candidate.number)
  const emphasized = new Set(emphasizedNumbers(timeline.round, candidates))
  const domain = yDomain(rows, numbers)
  const decided = decision(timeline)
  const offsets = labelOffsets(
    [...emphasized].map((number) => ({
      number,
      share: rows[rows.length - 1][seriesKey(number)],
    })),
    domain,
    plotHeight(height)
  )
  const config: ChartConfig = Object.fromEntries(
    candidates.map((candidate) => [
      seriesKey(candidate.number),
      {
        label: candidate.name,
        color: candidateColor(palette, candidate.number),
      },
    ])
  )

  return (
    <figure className="space-y-3">
      <ChartContainer
        config={config}
        role="img"
        aria-label={chartSummary(timeline, candidates)}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <LineChart data={rows} margin={MARGIN} accessibilityLayer>
          <CartesianGrid vertical={false} strokeDasharray="2 4" />
          <XAxis
            dataKey="progress"
            type="number"
            domain={[0, 1]}
            ticks={PROGRESS_TICKS}
            tickFormatter={formatPercentTick}
            tickLine={false}
            axisLine={false}
            height={X_AXIS_HEIGHT}
          />
          <YAxis
            domain={domain}
            ticks={yTicks(domain)}
            tickFormatter={formatPercentTick}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <ReferenceLine
            y={MAJORITY}
            stroke="var(--muted-foreground)"
            strokeOpacity={0.7}
          />
          {decided && (
            <ReferenceLine
              x={decided.progress}
              stroke="var(--foreground)"
              strokeDasharray="3 3"
              label={{
                value: "Mat. definido",
                position: decisionLabelPosition(decided.progress),
                fill: "var(--muted-foreground)",
                fontSize: 11,
              }}
            />
          )}
          <ChartTooltip
            cursor={{ strokeDasharray: "2 2" }}
            content={
              <TimelineTooltip candidates={candidates} palette={palette} />
            }
          />
          {candidates.map((candidate) => {
            const key = seriesKey(candidate.number)
            const strong = emphasized.has(candidate.number)
            return (
              <Line
                key={key}
                dataKey={key}
                name={candidate.name}
                type="linear"
                stroke={`var(--color-${key})`}
                strokeWidth={strong ? 2.5 : 1.25}
                strokeOpacity={strong ? 1 : 0.45}
                dot={false}
                activeDot={{ r: 3 }}
                isAnimationActive={false}
                label={
                  strong ? (
                    <EndLabel
                      lastIndex={rows.length - 1}
                      color={`var(--color-${key})`}
                      offset={Number(offsets.get(candidate.number))}
                    />
                  ) : (
                    false
                  )
                }
              />
            )
          })}
        </LineChart>
      </ChartContainer>
      <figcaption>
        <TimelineLegend
          candidates={candidates}
          emphasized={emphasized}
          palette={palette}
        />
      </figcaption>
    </figure>
  )
}
