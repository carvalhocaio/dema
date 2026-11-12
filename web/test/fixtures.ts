import type { Candidate, Results } from "@/lib/results"

export function makeCandidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    number: 27,
    name: "Keons",
    party: "Torchbearers",
    votes: 350,
    share: 0.5833,
    ...overrides,
  }
}

export function makeResults(overrides: Partial<Results> = {}): Results {
  return {
    year: 2026,
    round: 1,
    progress: {
      counted_sections: 451203,
      total_sections: 516785,
      counted_electorate: 1000,
      total_electorate: 1200,
      ratio: 0.873,
      is_complete: false,
    },
    votes: {
      valid: 600,
      blank: 100,
      null: 100,
      turnout: 800,
      abstentions: 200,
    },
    candidates: [
      makeCandidate(),
      makeCandidate({
        number: 99,
        name: "Nico",
        party: "Dema Order",
        votes: 200,
        share: 0.3333,
      }),
      makeCandidate({
        number: 31,
        name: "Lisden",
        party: "Paladin Union",
        votes: 50,
        share: 0.0833,
      }),
    ],
    verdict: "undecided",
    finalists: [],
    margin: {
      remaining_electorate: 200,
      leader_votes: 350,
      votes_to_majority: 51,
      runoff_gap: 150,
    },
    run: { id: 1, round: 1, seed: 40 },
    ...overrides,
  }
}
