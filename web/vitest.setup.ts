import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach, beforeEach, vi } from "vitest"

import { stubMatchMedia } from "@/test/media"

class NoopResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

beforeEach(() => {
  stubMatchMedia(() => false)
  vi.stubGlobal("ResizeObserver", NoopResizeObserver)
})

afterEach(() => {
  cleanup()
})
