import { screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { PipelinePanel } from "@/components/results/pipeline-panel"
import { renderWithProviders } from "@/test/render"
import { makePipeline } from "@/test/pipeline"

describe("PipelinePanel", () => {
  it("starts collapsed with a one-line summary", () => {
    renderWithProviders(<PipelinePanel pipeline={makePipeline()} />)

    const summary = screen.getByText("Bastidores").closest("summary")
    expect(summary).toHaveTextContent("612,4 BUs/s · 1 de 2 workers ativos")
    expect(summary?.parentElement).not.toHaveAttribute("open")
  })

  it("opens to show the stream, the group and each worker", async () => {
    renderWithProviders(<PipelinePanel pipeline={makePipeline()} />)

    await userEvent.click(screen.getByText("Bastidores"))

    const metric = (label: string) =>
      screen.getByText(label, { selector: "dt" }).nextElementSibling
    expect(metric("Rodada")).toHaveTextContent("#7 · seed 205504")
    expect(metric("Pico")).toHaveTextContent("1.480,0")
    expect(metric("Mensagens no stream")).toHaveTextContent("4.200")
    expect(metric("Atraso")).toHaveTextContent("120")
    expect(metric("Rejeitados")).toHaveTextContent("3")
    const rows = within(screen.getByRole("table")).getAllByRole("row")
    expect(rows[1]).toHaveTextContent("demo-0-0200agoraAtivo")
    expect(rows[2]).toHaveTextContent("demo-1-010042 sParado")
    expect(
      screen
        .getByRole("img", { name: /BUs por segundo, 3 amostras/ })
        .querySelector("polyline")
    ).toHaveAttribute("points", "0,48 120,16.65 240,0")
  })

  it("handles a pipeline without workers, lag or history", () => {
    renderWithProviders(
      <PipelinePanel
        pipeline={makePipeline({ consumers: [], lag: null, rates: [0] })}
      />
    )

    expect(
      screen.getByText("Nenhum worker conectado a esta rodada.")
    ).toBeInTheDocument()
    expect(
      screen.getByText("Atraso", { selector: "dt" }).nextElementSibling
    ).toHaveTextContent("—")
    expect(
      screen.getByRole("img", { hidden: true }).querySelector("polyline")
    ).toBeNull()
  })
})
