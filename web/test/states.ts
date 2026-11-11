import type { StateResult, States } from "@/lib/states"

export function stateResult(
  state: string,
  region: StateResult["region"],
  overrides: Partial<StateResult> = {}
): StateResult {
  return {
    state,
    region,
    counted_sections: 4,
    total_sections: 10,
    progress: 0.4,
    candidates: [
      { number: 27, votes: 500, share: 0.5 },
      { number: 99, votes: 400, share: 0.4 },
      { number: 31, votes: 100, share: 0.1 },
    ],
    leader: 27,
    ...overrides,
  }
}

export function makeStates(overrides: Partial<States> = {}): States {
  return {
    year: 2026,
    round: 1,
    states: [
      stateResult("SP", "southeast"),
      stateResult("BA", "northeast", {
        leader: 99,
        candidates: [
          { number: 99, votes: 600, share: 0.6 },
          { number: 27, votes: 400, share: 0.4 },
          { number: 31, votes: 0, share: 0 },
        ],
      }),
      stateResult("ZZ", "abroad", {
        counted_sections: 0,
        progress: 0,
        leader: null,
        candidates: [
          { number: 27, votes: 0, share: 0 },
          { number: 99, votes: 0, share: 0 },
          { number: 31, votes: 0, share: 0 },
        ],
      }),
    ],
    ...overrides,
  }
}
