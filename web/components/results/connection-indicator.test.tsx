import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { ConnectionIndicator } from "@/components/results/connection-indicator"
import { renderWithProviders } from "@/test/render"

describe("ConnectionIndicator", () => {
  it("pulses while live and reveals the API address on focus", async () => {
    renderWithProviders(<ConnectionIndicator label="Ao vivo" tone="live" />)

    const status = screen.getByRole("status")
    expect(status).toHaveTextContent("Ao vivo")
    expect(status.querySelector(".animate-ping")).not.toBeNull()

    await userEvent.tab()

    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "API: http://127.0.0.1:8000"
    )
  })

  it.each([
    ["warning", "bg-amber-500"],
    ["idle", "bg-muted-foreground/60"],
  ] as const)("shows a still %s dot", (tone, dotClass) => {
    renderWithProviders(<ConnectionIndicator label="x" tone={tone} />)

    const status = screen.getByRole("status")
    expect(status.querySelector(".animate-ping")).toBeNull()
    expect(status.querySelector(`.${CSS.escape(dotClass)}`)).not.toBeNull()
  })
})
