import { screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { RoundView } from "@/components/results/round-view"
import { FakeEventSource } from "@/test/event-source"
import { respond, routeFetch } from "@/test/fetch"
import { makeResults } from "@/test/fixtures"
import { renderWithProviders } from "@/test/render"
import { makeTimeline } from "@/test/timeline"

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal("EventSource", FakeEventSource)
})

describe("RoundView", () => {
  it("shows a skeleton until the first results arrive", () => {
    routeFetch({})
    const onReport = vi.fn()

    renderWithProviders(
      <RoundView
        round={{ round: 1, status: "live" }}
        hasFirstRound
        onReport={onReport}
      />
    )

    expect(screen.getByLabelText("Carregando resultados")).toBeInTheDocument()
    expect(onReport).toHaveBeenCalledWith({
      label: "Conectando",
      tone: "idle",
      year: null,
    })
  })

  it("explains a pending setup", async () => {
    routeFetch({ "/rounds/2/results": () => respond(503) })

    renderWithProviders(
      <RoundView
        round={{ round: 2, status: "live" }}
        hasFirstRound={false}
        onReport={vi.fn()}
      />
    )

    expect(
      await screen.findByText("Eleição ainda não preparada")
    ).toBeInTheDocument()
  })

  it("renders a finished round with its timeline and reports it", async () => {
    routeFetch({
      "/rounds/1/results": () =>
        respond(200, makeResults({ verdict: "runoff", finalists: [27, 99] })),
      "/rounds/1/timeline": () => respond(200, makeTimeline()),
    })
    const onReport = vi.fn()

    renderWithProviders(
      <RoundView
        round={{ round: 1, status: "final" }}
        hasFirstRound
        onReport={onReport}
      />
    )

    expect(
      await screen.findByText("2º turno: Keons × Nico")
    ).toBeInTheDocument()
    expect(
      await screen.findByText(
        /definido com 60,00% das seções totalizadas, após 30 min/
      )
    ).toBeInTheDocument()
    await waitFor(() =>
      expect(onReport).toHaveBeenLastCalledWith({
        label: "Resultado final",
        tone: "idle",
        year: 2026,
      })
    )
    expect(FakeEventSource.instances).toHaveLength(0)
  })
})
