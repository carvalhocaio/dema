import { render } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useFlip } from "@/hooks/use-flip"
import { stubMatchMedia } from "@/test/media"

const ROW_HEIGHT = 100

function List({ keys }: { keys: string[] }) {
  const register = useFlip<HTMLLIElement>(keys)
  return (
    <ol>
      {keys.map((key, index) => (
        <li key={key} ref={register(key)} data-top={index * ROW_HEIGHT}>
          {key}
        </li>
      ))}
    </ol>
  )
}

const animate = vi.fn()

beforeEach(() => {
  animate.mockClear()
  Object.defineProperty(HTMLElement.prototype, "offsetTop", {
    configurable: true,
    get(this: HTMLElement) {
      return Number(this.dataset.top ?? 0)
    },
  })
  Object.defineProperty(HTMLElement.prototype, "animate", {
    configurable: true,
    value: animate,
  })
})

afterEach(() => {
  Reflect.deleteProperty(HTMLElement.prototype, "offsetTop")
  Reflect.deleteProperty(HTMLElement.prototype, "animate")
})

function movedRows() {
  return animate.mock.calls.map(([keyframes]) => keyframes[0].transform).sort()
}

describe("useFlip", () => {
  it("does not animate the first render", () => {
    render(<List keys={["a", "b"]} />)

    expect(animate).not.toHaveBeenCalled()
  })

  it("slides swapped rows from their previous position", () => {
    const { rerender } = render(<List keys={["a", "b", "c"]} />)

    rerender(<List keys={["b", "a", "c"]} />)

    expect(movedRows()).toEqual(
      ["translateY(-100px)", "translateY(100px)"].sort()
    )
    expect(animate.mock.calls[0][1]).toMatchObject({ duration: 450 })
  })

  it("skips the animation when reduced motion is requested", () => {
    stubMatchMedia((query) => query.includes("reduce"))
    const { rerender } = render(<List keys={["a", "b"]} />)

    rerender(<List keys={["b", "a"]} />)

    expect(animate).not.toHaveBeenCalled()
  })

  it("forgets rows that leave the list", () => {
    const { rerender } = render(<List keys={["a", "b"]} />)

    rerender(<List keys={["b"]} />)

    expect(movedRows()).toEqual(["translateY(100px)"])
  })
})
