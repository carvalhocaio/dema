import { render, screen, within } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { ApiUnavailableNotice } from "@/components/results/api-unavailable-notice"
import { CandidateList } from "@/components/results/candidate-list"
import { ProgressPanel } from "@/components/results/progress-panel"
import { ResultsBoard } from "@/components/results/results-board"
import { ShareBar } from "@/components/results/share-bar"
import { VerdictBanner } from "@/components/results/verdict-banner"
import { VoteBreakdown } from "@/components/results/vote-breakdown"
import { makeResults } from "@/test/fixtures"

const PALETTE = [27, 31, 99]

describe("ProgressPanel", () => {
  it("shows the counted share with pt-BR numbers", () => {
    render(<ProgressPanel progress={makeResults().progress} />)

    expect(screen.getByText("87,30%")).toBeInTheDocument()
    expect(screen.getByText("451.203")).toBeInTheDocument()
    expect(screen.getByRole("progressbar")).toBeInTheDocument()
    expect(screen.queryByText("Totalização concluída")).toBeNull()
  })

  it("marks a finished count", () => {
    const { progress } = makeResults()
    render(<ProgressPanel progress={{ ...progress, is_complete: true }} />)

    expect(screen.getByText("Totalização concluída")).toBeInTheDocument()
  })
})

describe("VerdictBanner", () => {
  it("renders nothing while undecided", () => {
    const { container } = render(
      <VerdictBanner
        results={makeResults()}
        palette={PALETTE}
        decision={null}
      />
    )

    expect(container).toBeEmptyDOMElement()
  })

  it("names the runoff finalists", () => {
    render(
      <VerdictBanner
        palette={PALETTE}
        decision={null}
        results={makeResults({ verdict: "runoff", finalists: [27, 99] })}
      />
    )

    expect(screen.getByText("2º turno: Keons × Nico")).toBeInTheDocument()
    expect(
      screen.getByText(/Matematicamente definido com 87,30%/)
    ).toBeInTheDocument()
  })
})

describe("CandidateList", () => {
  it("lists candidates in the received order without badges while undecided", () => {
    render(<CandidateList results={makeResults()} palette={PALETTE} />)

    const rows = screen.getAllByRole("listitem")
    expect(
      rows.map((row) => within(row).getByText(/^\d+$/).textContent)
    ).toEqual(["27", "99", "31"])
    expect(screen.queryByText("2º turno")).toBeNull()
  })

  it("badges finalists and recedes the others after a verdict", () => {
    render(
      <CandidateList
        palette={PALETTE}
        results={makeResults({ verdict: "elected", finalists: [27] })}
      />
    )

    const [winner, , third] = screen.getAllByRole("listitem")
    expect(within(winner).getByText("Eleito")).toBeInTheDocument()
    expect(winner.firstElementChild).not.toHaveClass("opacity-50")
    expect(third.firstElementChild).toHaveClass("opacity-50")
  })
})

describe("ShareBar", () => {
  it.each([
    [0.4, "40%"],
    [1.5, "100%"],
    [-0.2, "0%"],
  ])("clamps a share of %s to a width of %s", (share, width) => {
    const { container } = render(<ShareBar share={share} color="red" />)

    const fill = container.firstElementChild
      ?.firstElementChild as HTMLElement | null
    expect(fill?.style.width).toBe(width)
  })
})

describe("VoteBreakdown", () => {
  it("states the base of every percentage", () => {
    render(<VoteBreakdown results={makeResults()} />)

    expect(screen.getByText("Válidos")).toBeInTheDocument()
    expect(screen.getByText("75,00%")).toBeInTheDocument()
    expect(screen.getAllByText("do comparecimento")).toHaveLength(3)
    expect(screen.getAllByText("do eleitorado apurado")).toHaveLength(2)
  })
})

describe("ApiUnavailableNotice", () => {
  it("tells whether the last score is still shown", () => {
    const { rerender } = render(<ApiUnavailableNotice hasData={false} />)
    expect(screen.getByRole("alert")).toHaveTextContent("Tentando novamente…")

    rerender(<ApiUnavailableNotice hasData />)
    expect(screen.getByRole("alert")).toHaveTextContent(
      "último placar recebido"
    )
  })
})

describe("ResultsBoard", () => {
  it("stacks progress, verdict, timeline, candidates and votes", () => {
    render(
      <ResultsBoard
        palette={PALETTE}
        timeline={null}
        results={makeResults({ verdict: "runoff", finalists: [27, 99] })}
      />
    )

    expect(
      screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)
    ).toEqual([
      "Seções totalizadas",
      "Minuto a minuto · % dos votos válidos",
      "Candidatos · % dos votos válidos",
      "Votos",
    ])
    expect(
      screen.getByText("Aguardando os primeiros boletins.")
    ).toBeInTheDocument()
    expect(screen.getByText("2º turno: Keons × Nico")).toBeInTheDocument()
  })
})

describe("VerdictBanner with a timeline", () => {
  it("dates the decision from the minute it was secured", () => {
    render(
      <VerdictBanner
        palette={PALETTE}
        decision={{ progress: 0.4312, elapsed: 141 * 60_000 }}
        results={makeResults({ verdict: "runoff", finalists: [27, 99] })}
      />
    )

    expect(
      screen.getByText(
        "Matematicamente definido com 43,12% das seções totalizadas, após 2h21 de apuração."
      )
    ).toBeInTheDocument()
  })
})
