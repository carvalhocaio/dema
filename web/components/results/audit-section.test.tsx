import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { AuditSection } from "@/components/results/audit-section"
import { makeBallot, makeRejection } from "@/test/audit"
import { respond, routeFetch, type FetchResponse } from "@/test/fetch"
import { renderWithProviders } from "@/test/render"

function serve(
  section: () => FetchResponse = () => respond(200, makeBallot()),
  tamper: () => FetchResponse = () =>
    respond(202, {
      section: "AC-10025-0001-0002",
      source: "SP-71072-0001-0042",
    }),
  rejected: () => FetchResponse = () =>
    respond(200, [
      makeRejection(),
      makeRejection({ entry: "2-0", reason: "malformed entry", section: null }),
    ])
) {
  return routeFetch({
    "/rounds/1/sections/SP-71072-0001-0042": section,
    "/rounds/1/sections/random": section,
    "/rounds/1/rejected": rejected,
    "/rounds/1/tamper": tamper,
  })
}

describe("AuditSection", () => {
  it("looks a ballot up and shows its signature seal", async () => {
    serve()
    renderWithProviders(
      <AuditSection round={1} canTamper={false} revision={null} />
    )

    await userEvent.type(
      screen.getByLabelText("Chave da seção"),
      "sp-71072-1-42"
    )
    await userEvent.click(screen.getByRole("button", { name: /Consultar/ }))

    const card = await screen.findByRole("article", {
      name: "Boletim da seção SP-71072-0001-0042",
    })
    expect(within(card).getByText("Assinatura válida")).toBeInTheDocument()
    expect(within(card).getByText("99 · Nico")).toBeInTheDocument()
    expect(within(card).getByText("17:03:00")).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: /Injetar BU adulterado/ })
    ).not.toBeInTheDocument()
  })

  it("draws a random section and flags signatures it could not trust", async () => {
    let ballot = makeBallot({ verified: false })
    serve(() => respond(200, ballot))
    renderWithProviders(
      <AuditSection round={1} canTamper={false} revision={null} />
    )
    const draw = screen.getByRole("button", { name: /Seção aleatória/ })

    await userEvent.click(draw)
    const card = await screen.findByRole("article")
    expect(within(card).getByText("Assinatura inválida")).toBeInTheDocument()

    ballot = makeBallot({ verified: null })
    await userEvent.click(draw)
    expect(
      await screen.findByText("Assinatura não conferida")
    ).toBeInTheDocument()
  })

  it("explains invalid keys, sections still to count and failures", async () => {
    let section = respond(404)
    serve(() => section)
    renderWithProviders(
      <AuditSection round={1} canTamper={false} revision={null} />
    )
    const input = screen.getByLabelText("Chave da seção")
    const search = screen.getByRole("button", { name: /Consultar/ })

    await userEvent.type(input, "SP 71072")
    await userEvent.click(search)
    expect(screen.getByRole("status")).toHaveTextContent("Chave inválida")

    await userEvent.clear(input)
    await userEvent.type(input, "SP-71072-0001-0042")
    await userEvent.click(search)
    expect(await screen.findByText(/ainda não foi apurada/)).toBeInTheDocument()

    await userEvent.click(
      screen.getByRole("button", { name: /Seção aleatória/ })
    )
    expect(
      await screen.findByText("Nenhuma seção foi apurada neste turno ainda.")
    ).toBeInTheDocument()

    section = respond(500)
    await userEvent.click(search)
    expect(
      await screen.findByText("Não foi possível consultar o boletim.")
    ).toBeInTheDocument()
  })

  it("lists the rejections with readable reasons", async () => {
    serve()
    renderWithProviders(
      <AuditSection round={1} canTamper={false} revision={3} />
    )

    const list = await screen.findByRole("list", {
      name: "Boletins rejeitados",
    })
    const items = within(list).getAllByRole("listitem")
    expect(items[0]).toHaveTextContent("Assinatura inválida")
    expect(items[0]).toHaveTextContent("AC-10025-0001-0002")
    expect(items[1]).toHaveTextContent("Entrada malformada")
    expect(items[1]).toHaveTextContent("seção ilegível")
  })

  it("says when nothing was rejected", async () => {
    serve(undefined, undefined, () => respond(200, []))
    renderWithProviders(
      <AuditSection round={1} canTamper={false} revision={null} />
    )

    expect(
      await screen.findByText("Nenhum boletim rejeitado neste turno.")
    ).toBeInTheDocument()
  })

  it("injects a tampered ballot and reports the outcome", async () => {
    let tamper = respond(202, {
      section: "AC-10025-0001-0002",
      source: "SP-71072-0001-0042",
    })
    serve(undefined, () => tamper)
    renderWithProviders(<AuditSection round={1} canTamper revision={null} />)
    const button = screen.getByRole("button", { name: /Injetar BU adulterado/ })

    await userEvent.click(button)
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "BU adulterado enviado para a seção AC-10025-0001-0002"
      )
    )

    tamper = respond(409)
    await userEvent.click(button)
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "Não há seção disponível para adulterar agora."
      )
    )

    tamper = respond(500)
    await userEvent.click(button)
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "Não foi possível injetar o BU adulterado."
      )
    )
  })
})
