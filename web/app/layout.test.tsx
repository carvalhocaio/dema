import { isValidElement, type ReactElement } from "react"
import { describe, expect, it, vi } from "vitest"

vi.mock("next/font/google", () => ({
  Geist: () => ({ variable: "geist-sans-variable" }),
  Geist_Mono: () => ({ variable: "geist-mono-variable" }),
}))

const { default: RootLayout, metadata } = await import("@/app/layout")

describe("RootLayout", () => {
  it("renders a Portuguese document with both font variables", () => {
    const html = RootLayout({ children: <main /> }) as ReactElement<{
      lang: string
      className: string
    }>

    expect(isValidElement(html)).toBe(true)
    expect(html.props.lang).toBe("pt-BR")
    expect(html.props.className).toContain("geist-sans-variable")
    expect(html.props.className).toContain("geist-mono-variable")
  })

  it("describes the page", () => {
    expect(metadata.title).toBe("Apuração · Eleição 2026")
  })
})
