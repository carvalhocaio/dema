import { screen, within } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { StateList } from "@/components/results/state-list"
import { StateMap } from "@/components/results/state-map"
import { StatesSection } from "@/components/results/states-section"
import { makeResults } from "@/test/fixtures"
import { renderWithProviders } from "@/test/render"
import { makeStates } from "@/test/states"

const CANDIDATES = makeResults().candidates
const PALETTE = [27, 31, 99]

describe("StateMap", () => {
  it("draws one tile per state with sigla, share and the leader's color", async () => {
    renderWithProviders(
      <StateMap
        states={makeStates()}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )

    const map = screen.getByRole("img", { name: /Mapa por estado/ })
    const tiles = within(map).getAllByText(/^[A-Z]{2}$/)
    expect(tiles).toHaveLength(28)
    const sp = within(map).getByText("SP").parentElement as HTMLElement
    expect(sp).toHaveTextContent("40%")
    expect(sp.getAttribute("style")).toContain("var(--candidate-1)")
    const zz = within(map).getByText("ZZ").parentElement as HTMLElement
    expect(zz).toHaveTextContent("—")
    const ac = within(map).getByText("AC").parentElement as HTMLElement
    expect(ac).toHaveTextContent("—")

    sp.focus()
    const tooltip = await screen.findByRole("tooltip")
    expect(tooltip).toHaveTextContent("SP · 40,00% apurado")
    expect(tooltip).toHaveTextContent("Keons")
    expect(tooltip).toHaveTextContent("50,00%")
  })

  it("falls back to the ballot number for unknown candidates", async () => {
    renderWithProviders(
      <StateMap states={makeStates()} candidates={[]} palette={PALETTE} />
    )
    const map = screen.getByRole("img", { name: /Mapa por estado/ })

    ;(within(map).getByText("SP").parentElement as HTMLElement).focus()

    expect(await screen.findByRole("tooltip")).toHaveTextContent("27 50,00%")
  })

  it("explains a state without ballots on focus", async () => {
    renderWithProviders(
      <StateMap
        states={makeStates()}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )
    const map = screen.getByRole("img", { name: /Mapa por estado/ })

    ;(within(map).getByText("AC").parentElement as HTMLElement).focus()

    expect(await screen.findByRole("tooltip")).toHaveTextContent(/AC/)
  })
})

describe("StateList", () => {
  it("lists the leader and counted share per region", () => {
    renderWithProviders(
      <StateList
        states={makeStates()}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )

    expect(screen.getByText("Nordeste")).toBeInTheDocument()
    const ba = screen.getByText("BA").parentElement as HTMLElement
    expect(ba).toHaveTextContent("Nico")
    const zz = screen.getByText("ZZ").parentElement as HTMLElement
    expect(zz).toHaveTextContent("—")
    expect(zz).toHaveTextContent("0,00%")
  })
})

describe("StatesSection", () => {
  it("waits for the first ballots", () => {
    renderWithProviders(
      <StatesSection states={null} candidates={CANDIDATES} palette={PALETTE} />
    )
    expect(
      screen.getByText("Aguardando os primeiros boletins.")
    ).toBeInTheDocument()
  })

  it("shows the map, the region legend and the list", () => {
    renderWithProviders(
      <StatesSection
        states={makeStates()}
        candidates={CANDIDATES}
        palette={PALETTE}
      />
    )
    expect(
      screen.getByRole("img", { name: /Mapa por estado/ })
    ).toBeInTheDocument()
    expect(screen.getByRole("list", { name: "Regiões" })).toHaveTextContent(
      "Sudeste SP"
    )
  })
})
