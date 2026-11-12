CREATE TABLE runs (
    id serial PRIMARY KEY,
    year smallint NOT NULL,
    round smallint NOT NULL,
    seed bigint NOT NULL CHECK (seed >= 0),
    status text NOT NULL
        CHECK (status IN ('preparing', 'counting', 'complete', 'superseded')),
    candidates smallint[] NOT NULL,
    parent_id integer REFERENCES runs,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    FOREIGN KEY (year, round) REFERENCES elections
);

CREATE TABLE active_run (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    run_id integer NOT NULL REFERENCES runs
);

INSERT INTO runs (year, round, seed, status, candidates, finished_at)
SELECT
    e.year, e.round, 0, 'complete',
    ARRAY(
        SELECT c.number FROM candidates AS c
        WHERE (c.year, c.round) = (e.year, e.round)
        ORDER BY c.number
    ),
    now()
FROM elections AS e
ORDER BY e.year, e.round;

UPDATE runs AS r SET parent_id = p.id
FROM runs AS p
WHERE r.round = 2 AND p.round = 1 AND p.year = r.year;

INSERT INTO active_run (run_id)
SELECT id FROM runs ORDER BY year DESC, round DESC LIMIT 1;

ALTER TABLE ballot_votes DROP CONSTRAINT ballot_votes_year_round_section_fkey;
ALTER TABLE ballot_votes DROP CONSTRAINT ballot_votes_pkey;
ALTER TABLE ballots DROP CONSTRAINT ballots_pkey;
ALTER TABLE ballots DROP CONSTRAINT ballots_section_fkey;

ALTER TABLE ballots ADD COLUMN run_id integer REFERENCES runs;
UPDATE ballots AS b SET run_id = r.id
FROM runs AS r WHERE (r.year, r.round) = (b.year, b.round);
ALTER TABLE ballots
    ALTER COLUMN run_id SET NOT NULL,
    ADD PRIMARY KEY (run_id, section),
    ADD FOREIGN KEY (section) REFERENCES sections (key) ON DELETE CASCADE;

ALTER TABLE ballot_votes ADD COLUMN run_id integer;
UPDATE ballot_votes AS v SET run_id = r.id
FROM runs AS r WHERE (r.year, r.round) = (v.year, v.round);
ALTER TABLE ballot_votes
    ALTER COLUMN run_id SET NOT NULL,
    ADD PRIMARY KEY (run_id, section, candidate),
    ADD FOREIGN KEY (run_id, section)
        REFERENCES ballots (run_id, section) ON DELETE CASCADE;

ALTER TABLE minute_totals ADD COLUMN run_id integer REFERENCES runs;
UPDATE minute_totals AS t SET run_id = r.id
FROM runs AS r WHERE (r.year, r.round) = (t.year, t.round);
ALTER TABLE minute_totals
    DROP CONSTRAINT minute_totals_pkey,
    ALTER COLUMN run_id SET NOT NULL,
    ADD PRIMARY KEY (run_id, minute);

ALTER TABLE minute_votes ADD COLUMN run_id integer REFERENCES runs;
UPDATE minute_votes AS t SET run_id = r.id
FROM runs AS r WHERE (r.year, r.round) = (t.year, t.round);
ALTER TABLE minute_votes
    DROP CONSTRAINT minute_votes_pkey,
    ALTER COLUMN run_id SET NOT NULL,
    ADD PRIMARY KEY (run_id, minute, candidate);

ALTER TABLE state_totals ADD COLUMN run_id integer REFERENCES runs;
UPDATE state_totals AS t SET run_id = r.id
FROM runs AS r WHERE (r.year, r.round) = (t.year, t.round);
ALTER TABLE state_totals
    DROP CONSTRAINT state_totals_pkey,
    ALTER COLUMN run_id SET NOT NULL,
    ADD PRIMARY KEY (run_id, state);

ALTER TABLE state_votes ADD COLUMN run_id integer REFERENCES runs;
UPDATE state_votes AS t SET run_id = r.id
FROM runs AS r WHERE (r.year, r.round) = (t.year, t.round);
ALTER TABLE state_votes
    DROP CONSTRAINT state_votes_pkey,
    ALTER COLUMN run_id SET NOT NULL,
    ADD PRIMARY KEY (run_id, state, candidate);
