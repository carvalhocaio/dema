import { screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { ResultsScreen } from "@/components/results/results-screen"
import type { ResultsState } from "@/hooks/use-results"
import { makeResults } from "@/test/fixtures"
import { renderWithProviders } from "@/test/render"

const state = vi.hoisted(() => ({ current: null as ResultsState | null }))

vi.mock("@/hooks/use-results", () => ({
  useResults: () => state.current,
}))

function renderScreen(next: ResultsState) {
  state.current = next
  return renderWithProviders(<ResultsScreen />)
}

describe("ResultsScreen", () => {
  it("shows a skeleton while connecting, with default headings", () => {
    renderScreen({ results: null, connection: "connecting", setup: "unknown" })

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Apuração · Eleição 2026"
    )
    expect(screen.getByText("Presidente · 1º turno")).toBeInTheDocument()
    expect(screen.getByLabelText("Carregando resultados")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("explains how to set up the election", () => {
    renderScreen({ results: null, connection: "live", setup: "pending" })

    expect(screen.getByText("Eleição ainda não preparada")).toBeInTheDocument()
    expect(screen.getByText("Aguardando setup")).toBeInTheDocument()
  })

  it("warns when the API is down", () => {
    renderScreen({ results: null, connection: "unavailable", setup: "unknown" })

    expect(screen.getByRole("alert")).toHaveTextContent("Tentando novamente…")
  })

  it("renders the board from the round being counted", () => {
    renderScreen({
      results: makeResults({ year: 2030, round: 2 }),
      connection: "live",
      setup: "ready",
    })

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Apuração · Eleição 2030"
    )
    expect(screen.getByText("Presidente · 2º turno")).toBeInTheDocument()
    expect(
      screen.getByText("Seções totalizadas", { selector: "h2" })
    ).toBeInTheDocument()
  })
})
