import { act, render, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { ThemeProvider } from "@/components/theme-provider"

function renderProvider() {
  return render(
    <ThemeProvider defaultTheme="light" enableSystem={false}>
      <input aria-label="field" />
      <textarea aria-label="notes" />
      <select aria-label="choice" />
      <div aria-label="editable" />
    </ThemeProvider>
  )
}

function press(target: EventTarget, init: KeyboardEventInit = {}) {
  act(() => {
    target.dispatchEvent(
      new KeyboardEvent("keydown", { key: "d", bubbles: true, ...init })
    )
  })
}

function isDark() {
  return document.documentElement.classList.contains("dark")
}

describe("ThemeProvider", () => {
  it("toggles the theme with the d key", async () => {
    renderProvider()

    press(window, { key: "D" })
    await waitFor(() => expect(isDark()).toBe(true))

    press(window)
    await waitFor(() => expect(isDark()).toBe(false))
  })

  it("ignores modified, repeated, prevented and unrelated keys", () => {
    renderProvider()

    press(window, { metaKey: true })
    press(window, { ctrlKey: true })
    press(window, { altKey: true })
    press(window, { repeat: true })
    press(window, { key: "x" })
    const prevented = new KeyboardEvent("keydown", {
      key: "d",
      cancelable: true,
    })
    prevented.preventDefault()
    act(() => {
      window.dispatchEvent(prevented)
    })

    expect(isDark()).toBe(false)
  })

  it("ignores the key while typing", () => {
    const { getByLabelText } = renderProvider()
    const editable = getByLabelText("editable")
    Object.defineProperty(editable, "isContentEditable", { value: true })

    for (const label of ["field", "notes", "choice", "editable"]) {
      press(getByLabelText(label))
    }

    expect(isDark()).toBe(false)
  })
})
