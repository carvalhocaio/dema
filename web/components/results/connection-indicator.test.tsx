import { screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { ConnectionIndicator } from "@/components/results/connection-indicator"
import { renderWithProviders } from "@/test/render"

describe("ConnectionIndicator", () => {
  it("pulses while live", () => {
    renderWithProviders(
      <ConnectionIndicator label="Ao vivo" tone="live" className="text-xs" />
    )

    const status = screen.getByRole("status")
    expect(status).toHaveTextContent("Ao vivo")
    expect(status).toHaveClass("text-xs")
    expect(status.querySelector(".animate-ping")).not.toBeNull()
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
