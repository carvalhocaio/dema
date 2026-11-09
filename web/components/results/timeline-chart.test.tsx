import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { TimelineChart } from "@/components/results/timeline-chart"
import {
  EndLabel,
  TimelineLegend,
  TimelineTooltip,
} from "@/components/results/timeline-parts"
import { TimelineSection } from "@/components/results/timeline-section"
import { chartRows } from "@/lib/timeline"
import { makeResults } from "@/test/fixtures"
import { makeTimeline } from "@/test/timeline"

const CANDIDATES = makeResults().candidates
const PALETTE = [27, 31, 99]
const SIZE = { width: 640, height: 288 }

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect(SIZE)
  )
})

function renderChart(timeline = makeTimeline()) {
  return render(
    <TimelineChart
      timeline={timeline}
      candidates={CANDIDATES}
      palette={PALETTE}
    />
  )
}

describe("TimelineChart", () => {
  it("summarises the race for assistive technology", () => {
    renderChart()

    expect(screen.getByRole("img")).toHaveAccessibleName(
      /Keons lidera com 50,00% dos votos válidos desde 17:30/
    )
  })

  it("draws one line per candidate, labels the leaders and marks the decision", () => {
    const { container } = renderChart()

    expect(container.querySelectorAll(".recharts-line")).toHaveLength(3)
    expect(screen.getByText("50,00%")).toBeInTheDocument()
    expect(screen.getByText("40,00%")).toBeInTheDocument()
    expect(screen.queryByText("10,00%")).toBeNull()
    expect(screen.getByText("Mat. definido")).toBeInTheDocument()
  })

  it("leaves the decision line out while the result is open", () => {
    renderChart(makeTimeline({ decided_at: null }))

    expect(screen.queryByText("Mat. definido")).toBeNull()
  })

  it("stresses every runoff candidate", () => {
    renderChart(makeTimeline({ round: 2 }))

    expect(screen.getByText("10,00%")).toBeInTheDocument()
  })
})

describe("EndLabel", () => {
  it("only labels the last point", () => {
    const { container } = render(
      <svg>
        <EndLabel
          x={10}
          y={20}
          index={0}
          value={0.4}
          lastIndex={2}
          color="red"
          offset={0}
        />
        <EndLabel
          x={10}
          y={20}
          index={2}
          value={0.4}
          lastIndex={2}
          color="red"
          offset={5}
        />
      </svg>
    )

    const [label] = container.querySelectorAll("text")
    expect(container.querySelectorAll("text")).toHaveLength(1)
    expect(label).toHaveAttribute("x", "16")
    expect(label).toHaveAttribute("y", "25")
  })
})

describe("TimelineTooltip", () => {
  const [row] = chartRows(makeTimeline())

  it("lists the time, counted sections and every share", () => {
    render(
      <TimelineTooltip
        active
        payload={[{ payload: row }]}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )

    expect(screen.getByText("17:00 · 10,00% das seções")).toBeInTheDocument()
    expect(
      screen.getAllByRole("listitem").map((item) => item.textContent)
    ).toEqual(["Nico50,00%", "Keons40,00%", "Lisden10,00%"])
  })

  it.each([
    ["inactive", { active: false, payload: [{ payload: row }] }],
    ["without payload", { active: true }],
    ["with an empty payload", { active: true, payload: [] }],
    ["without a row", { active: true, payload: [{}] }],
  ])("renders nothing when %s", (_, props) => {
    const { container } = render(
      <TimelineTooltip {...props} candidates={CANDIDATES} palette={PALETTE} />
    )

    expect(container).toBeEmptyDOMElement()
  })
})

describe("TimelineLegend", () => {
  it("names every series and dims the secondary ones", () => {
    render(
      <TimelineLegend
        candidates={CANDIDATES}
        emphasized={new Set([27])}
        palette={PALETTE}
      />
    )

    expect(screen.getByText("Keons (27)")).toHaveClass("font-medium")
    expect(screen.getByText("Nico (99)")).toHaveClass("text-muted-foreground")
  })
})

describe("TimelineSection", () => {
  it("waits for the first ballots", () => {
    render(
      <TimelineSection
        timeline={null}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )
    render(
      <TimelineSection
        timeline={makeTimeline({ points: [] })}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )

    expect(
      screen.getAllByText("Aguardando os primeiros boletins.")
    ).toHaveLength(2)
  })

  it("shows the chart once points arrive", () => {
    render(
      <TimelineSection
        timeline={makeTimeline()}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )

    expect(screen.getByRole("img")).toBeInTheDocument()
  })
})
