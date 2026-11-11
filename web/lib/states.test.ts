import { describe, expect, it } from "vitest"

import {
  byRegion,
  describeTile,
  GRID_COLUMNS,
  GRID_ROWS,
  REGION_ORDER,
  statesSummary,
  TILES,
  tileIntensity,
  topTwo,
} from "@/lib/states"
import { makeResults } from "@/test/fixtures"
import { makeStates, stateResult } from "@/test/states"

const CANDIDATES = makeResults().candidates

describe("tile grid", () => {
  it("places every state and the abroad tile inside the grid once", () => {
    const states = TILES.map((tile) => tile.state)
    expect(new Set(states).size).toBe(28)
    expect(states).toContain("ZZ")
    for (const tile of TILES) {
      expect(tile.column).toBeGreaterThanOrEqual(1)
      expect(tile.column).toBeLessThanOrEqual(GRID_COLUMNS)
      expect(tile.row).toBeGreaterThanOrEqual(1)
      expect(tile.row).toBeLessThanOrEqual(GRID_ROWS)
    }
    const cells = TILES.map((tile) => `${tile.column},${tile.row}`)
    expect(new Set(cells).size).toBe(TILES.length)
  })

  it("grows the intensity with the counted share and stays neutral at zero", () => {
    expect(tileIntensity(0)).toBe(0)
    expect(tileIntensity(0.5)).toBeGreaterThan(tileIntensity(0.1))
    expect(tileIntensity(1)).toBe(1)
  })
})

describe("grouping and ranking", () => {
  it("keeps the two leading candidates of a state", () => {
    expect(topTwo(stateResult("SP", "southeast")).map((c) => c.number)).toEqual(
      [27, 99]
    )
  })

  it("groups states by region in the canonical order", () => {
    const groups = byRegion(makeStates().states)

    expect([...groups.keys()]).toEqual(REGION_ORDER)
    expect(groups.get("southeast")?.map((s) => s.state)).toEqual(["SP"])
    expect(groups.get("north")).toEqual([])
  })
})

describe("text summaries", () => {
  it("names who leads in how many states and the pending ones", () => {
    expect(statesSummary(makeStates(), CANDIDATES)).toBe(
      "Mapa por estado: Keons lidera em 1, Nico lidera em 1; 1 sem apuração."
    )
  })

  it("handles an empty count and unknown candidates", () => {
    expect(statesSummary(makeStates({ states: [] }), CANDIDATES)).toBe(
      "Mapa por estado: nenhum estado apurado."
    )
    expect(
      statesSummary(
        makeStates({
          states: [stateResult("SP", "southeast", { leader: 55 })],
        }),
        CANDIDATES
      )
    ).toContain("ninguém lidera em 1")
  })

  it("describes a tile for its tooltip", () => {
    expect(describeTile(stateResult("SP", "southeast"), CANDIDATES)).toBe(
      "SP: 40,00% apurado. Keons 50,00%, Nico 40,00%."
    )
    expect(
      describeTile(
        stateResult("ZZ", "abroad", { progress: 0, candidates: [] }),
        CANDIDATES
      )
    ).toBe("ZZ: 0,00% apurado. Sem votos.")
    expect(
      describeTile(
        stateResult("SP", "southeast", {
          candidates: [{ number: 55, votes: 1, share: 1 }],
        }),
        CANDIDATES
      )
    ).toContain("55 100,00%")
  })
})
