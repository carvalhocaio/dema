import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { NewCountDialog } from "@/components/results/new-count-dialog"
import { RunBadge } from "@/components/results/run-badge"
import { respond, routeFetch } from "@/test/fetch"
import { renderWithProviders } from "@/test/render"

const RUN = { id: 3, round: 1, seed: 40, status: "counting" as const }

describe("RunBadge", () => {
  it("shows the run and copies its seed", async () => {
    const writeText = vi.fn(async () => {})
    vi.stubGlobal("navigator", { clipboard: { writeText } })
    renderWithProviders(<RunBadge run={RUN} />)

    expect(screen.getByText(/Rodada #3/)).toHaveTextContent(
      "Rodada #3 · seed 40"
    )
    await userEvent.click(screen.getByRole("button", { name: "Copiar seed" }))

    expect(writeText).toHaveBeenCalledWith("40")
    expect(
      screen.getByRole("button", { name: "Seed copiada" })
    ).toBeInTheDocument()
  })
})

async function openDialog() {
  const onStarted = vi.fn()
  renderWithProviders(<NewCountDialog onStarted={onStarted} />)
  await userEvent.click(screen.getByRole("button", { name: "Nova apuração" }))
  return onStarted
}

describe("NewCountDialog", () => {
  it("starts a count with the given seed and closes", async () => {
    const fetchMock = routeFetch({ "/runs": () => respond(202, RUN) })
    const onStarted = await openDialog()

    await userEvent.type(screen.getByLabelText("Seed (opcional)"), "40")
    await userEvent.click(screen.getByRole("button", { name: "Iniciar" }))

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(RUN))
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ body: '{"seed":40}' })
    expect(screen.queryByRole("dialog")).toBeNull()
  })

  it("explains an invalid seed without calling the API", async () => {
    const fetchMock = routeFetch({})
    const onStarted = await openDialog()

    await userEvent.type(screen.getByLabelText("Seed (opcional)"), "-3")
    await userEvent.click(screen.getByRole("button", { name: "Iniciar" }))

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A seed deve ser um número inteiro não negativo."
    )
    expect(fetchMock).not.toHaveBeenCalled()
    expect(onStarted).not.toHaveBeenCalled()
  })

  it("explains when the API is unreachable", async () => {
    routeFetch({ "/runs": () => new TypeError("offline") })
    await openDialog()

    await userEvent.click(screen.getByRole("button", { name: "Iniciar" }))

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível iniciar a apuração."
    )
  })

  it("can be dismissed", async () => {
    await openDialog()

    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }))

    expect(screen.queryByRole("dialog")).toBeNull()
  })
})
