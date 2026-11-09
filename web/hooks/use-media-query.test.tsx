import { act, renderHook } from "@testing-library/react"
import { renderToString } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { DESKTOP_QUERY, useMediaQuery } from "@/hooks/use-media-query"

function controllableMedia(initial: boolean) {
  const listeners = new Set<() => void>()
  const media = {
    matches: initial,
    addEventListener: vi.fn((_: string, listener: () => void) =>
      listeners.add(listener)
    ),
    removeEventListener: vi.fn((_: string, listener: () => void) =>
      listeners.delete(listener)
    ),
  }
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => media)
  )
  return {
    media,
    change(matches: boolean) {
      media.matches = matches
      listeners.forEach((listener) => listener())
    },
    listeners,
  }
}

describe("useMediaQuery", () => {
  it("follows the media query as it changes", () => {
    const control = controllableMedia(false)
    const { result, unmount } = renderHook(() => useMediaQuery(DESKTOP_QUERY))
    expect(result.current).toBe(false)

    act(() => control.change(true))
    expect(result.current).toBe(true)

    unmount()
    expect(control.listeners.size).toBe(0)
    expect(window.matchMedia).toHaveBeenCalledWith("(min-width: 1024px)")
  })

  it("assumes a small screen on the server", () => {
    controllableMedia(true)
    function Probe() {
      return <span>{String(useMediaQuery(DESKTOP_QUERY))}</span>
    }

    expect(renderToString(<Probe />)).toBe("<span>false</span>")
  })
})
