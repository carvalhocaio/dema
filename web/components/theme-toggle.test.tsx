import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { renderToString } from "react-dom/server"
import { beforeEach, describe, expect, it } from "vitest"

import { ThemeProvider } from "@/components/theme-provider"
import { ThemeToggle } from "@/components/theme-toggle"
import { renderWithProviders } from "@/test/render"

function renderToggle() {
  return renderWithProviders(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>
  )
}

const root = document.documentElement

beforeEach(() => {
  localStorage.clear()
  root.className = ""
})

describe("ThemeToggle", () => {
  it("starts following the system", () => {
    renderToggle()

    expect(screen.getByLabelText("Tema")).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: "Tema do sistema" })).toBeChecked()
    expect(root).toHaveClass("light")
  })

  it("switches between dark, light and back to the system", async () => {
    renderToggle()

    await userEvent.click(screen.getByRole("radio", { name: "Tema escuro" }))
    expect(root).toHaveClass("dark")
    expect(localStorage.getItem("theme")).toBe("dark")

    await userEvent.click(screen.getByRole("radio", { name: "Tema claro" }))
    expect(root).toHaveClass("light")
    expect(root).not.toHaveClass("dark")

    await userEvent.click(
      screen.getByRole("radio", { name: "Tema do sistema" })
    )
    expect(screen.getByRole("radio", { name: "Tema do sistema" })).toBeChecked()
  })

  it("keeps the current theme when its own button is pressed again", async () => {
    renderToggle()
    const dark = screen.getByRole("radio", { name: "Tema escuro" })

    await userEvent.click(dark)
    await userEvent.click(dark)

    expect(dark).toBeChecked()
    expect(root).toHaveClass("dark")
  })

  it("renders nothing selected on the server", () => {
    const html = renderToString(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    )

    expect(html).toContain('aria-label="Tema escuro"')
    expect(html).not.toContain('aria-checked="true"')
  })
})
