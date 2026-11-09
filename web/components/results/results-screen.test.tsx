import { act, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ResultsScreen } from "@/components/results/results-screen"
import { FakeEventSource } from "@/test/event-source"
import { respond, routeFetch } from "@/test/fetch"
import { makeResults } from "@/test/fixtures"
import { renderWithProviders } from "@/test/render"
import { makeTimeline } from "@/test/timeline"

const FIRST_ROUND = makeResults({ verdict: "runoff", finalists: [27, 99] })
const RUNOFF = makeResults({
  round: 2,
  candidates: FIRST_ROUND.candidates.slice(0, 2),
})

function serveTwoRounds() {
  return routeFetch({
    "/rounds": () =>
      respond(200, [
        { round: 1, status: "final" },
        { round: 2, status: "live" },
      ]),
    "/rounds/1/results": () => respond(200, FIRST_ROUND),
    "/rounds/2/results": () => respond(200, RUNOFF),
    "/rounds/1/timeline": () => respond(200, makeTimeline()),
    "/rounds/2/timeline": () => respond(200, makeTimeline({ round: 2 })),
  })
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal("EventSource", FakeEventSource)
  window.history.replaceState(null, "", "/")
})

afterEach(() => {
  window.history.replaceState(null, "", "/")
})

describe("ResultsScreen", () => {
  it("shows a skeleton while the rounds load", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {}))
    )

    renderWithProviders(<ResultsScreen />)

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Apuração · Eleição 2026"
    )
    expect(screen.getByText("Presidente · 1º turno")).toBeInTheDocument()
    expect(screen.getByLabelText("Carregando resultados")).toBeInTheDocument()
  })

  it("warns when the API is down", async () => {
    routeFetch({ "/rounds": () => new TypeError("offline") })

    renderWithProviders(<ResultsScreen />)

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Tentando novamente…"
    )
  })

  it("explains how to set up an election when no round exists", async () => {
    routeFetch({ "/rounds": () => respond(200, []) })

    renderWithProviders(<ResultsScreen />)

    expect(
      await screen.findByText("Eleição ainda não preparada")
    ).toBeInTheDocument()
  })

  it("opens the live round and follows its connection on the tab", async () => {
    serveTwoRounds()

    renderWithProviders(<ResultsScreen />)

    const live = await screen.findByRole("tab", { name: /2º turno/ })
    expect(live).toHaveAttribute("aria-selected", "true")
    expect(await screen.findByText("Presidente · 2º turno")).toBeInTheDocument()
    expect(within(live).getByRole("status")).toHaveTextContent("Ao vivo")

    act(() => FakeEventSource.latest().fail(FakeEventSource.CLOSED))

    expect(within(live).getByRole("status")).toHaveTextContent("Sem conexão")
  })

  it("switches rounds through the tabs and remembers the choice in the URL", async () => {
    serveTwoRounds()
    renderWithProviders(<ResultsScreen />)

    await userEvent.click(await screen.findByRole("tab", { name: "1º turno" }))

    expect(window.location.search).toBe("?turno=1")
    expect(
      await screen.findByText("2º turno: Keons × Nico")
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole("tab", { name: /2º turno/ })).getByRole("status")
    ).toHaveTextContent("Ao vivo")
  })

  it("opens the round requested in the URL and disables missing rounds", async () => {
    window.history.replaceState(null, "", "/?turno=2")
    routeFetch({
      "/rounds": () => respond(200, [{ round: 1, status: "live" }]),
      "/rounds/1/results": () => respond(200, FIRST_ROUND),
    })

    renderWithProviders(<ResultsScreen />)

    expect(await screen.findByRole("tab", { name: "2º turno" })).toBeDisabled()
    expect(screen.getByRole("tab", { name: /1º turno/ })).toHaveAttribute(
      "aria-selected",
      "true"
    )
  })
})

describe("ResultsScreen while rounds are still connecting", () => {
  it("keeps the header steady when switching between connecting rounds", async () => {
    window.history.replaceState(null, "", "/")
    routeFetch({
      "/rounds": () =>
        respond(200, [
          { round: 1, status: "final" },
          { round: 2, status: "live" },
        ]),
    })
    renderWithProviders(<ResultsScreen />)
    const first = await screen.findByRole("tab", { name: "1º turno" })

    await userEvent.click(first)

    expect(first).toHaveAttribute("aria-selected", "true")
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Apuração · Eleição 2026"
    )
  })
})
