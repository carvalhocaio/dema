import type { BallotAudit, Rejection } from "@/lib/audit"

export function makeBallot(overrides: Partial<BallotAudit> = {}): BallotAudit {
  return {
    section: "SP-71072-0001-0042",
    state: "SP",
    issued_at: "2026-10-04T20:03:00Z",
    received_at: "2026-10-04T20:03:02Z",
    eligible_voters: 300,
    candidates: [
      { number: 99, name: "Nico", votes: 150 },
      { number: 27, name: "Keons", votes: 120 },
    ],
    blank: 4,
    null: 6,
    signature: "ab".repeat(32),
    verified: true,
    ...overrides,
  }
}

export function makeRejection(overrides: Partial<Rejection> = {}): Rejection {
  return {
    entry: "1791230580000-0",
    at: "2026-10-04T20:03:00Z",
    reason: "invalid signature",
    section: "AC-10025-0001-0002",
    ...overrides,
  }
}
