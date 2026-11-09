import { createElement } from "react"
import { renderToString } from "react-dom/server"
import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"

import { useSelectedRound } from "@/hooks/use-selected-round"
import type { Round } from "@/lib/rounds"

const ROUNDS: Round[] = [
  { round: 1, status: "final" },
  { round: 2, status: "live" },
]

afterEach(() => {
  window.history.replaceState(null, "", "/")
})

describe("useSelectedRound", () => {
  it("starts on the live round", () => {
    const { result } = renderHook(() => useSelectedRound(ROUNDS))

    expect(result.current[0]?.round).toBe(2)
  })

  it("honours the round in the URL", () => {
    window.history.replaceState(null, "", "/?turno=1")

    const { result } = renderHook(() => useSelectedRound(ROUNDS))

    expect(result.current[0]?.round).toBe(1)
  })

  it("keeps the choice in the URL", () => {
    window.history.replaceState(null, "", "/?foo=bar")
    const { result } = renderHook(() => useSelectedRound(ROUNDS))

    act(() => result.current[1](1))

    expect(result.current[0]?.round).toBe(1)
    expect(window.location.search).toBe("?foo=bar&turno=1")
  })

  it("follows back and forward navigation", () => {
    const { result } = renderHook(() => useSelectedRound(ROUNDS))

    act(() => {
      window.history.pushState(null, "", "/?turno=1")
      window.dispatchEvent(new PopStateEvent("popstate"))
    })

    expect(result.current[0]?.round).toBe(1)
  })
})

describe("useSelectedRound on the server", () => {
  it("renders the live round without reading the URL", () => {
    function Probe() {
      const [selected] = useSelectedRound(ROUNDS)
      return createElement("span", null, selected?.round)
    }

    expect(renderToString(createElement(Probe))).toBe("<span>2</span>")
  })
})
