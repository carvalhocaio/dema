import { describe, expect, it } from "vitest"

import Page from "@/app/page"
import { ResultsScreen } from "@/components/results/results-screen"

describe("Page", () => {
  it("renders the results screen", () => {
    expect(Page().type).toBe(ResultsScreen)
  })
})
