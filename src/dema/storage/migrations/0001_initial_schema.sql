CREATE TABLE elections (
    year smallint NOT NULL,
    round smallint NOT NULL CHECK (round IN (1, 2)),
    polls_close timestamptz NOT NULL,
    PRIMARY KEY (year, round)
);

CREATE TABLE candidates (
    year smallint NOT NULL,
    round smallint NOT NULL,
    number smallint NOT NULL CHECK (number BETWEEN 10 AND 99),
    name text NOT NULL CHECK (btrim(name) <> ''),
    party text NOT NULL,
    birth_date date NOT NULL,
    PRIMARY KEY (year, round, number),
    FOREIGN KEY (year, round) REFERENCES elections
);

CREATE TABLE sections (
    state char(2) NOT NULL,
    municipality_code integer NOT NULL,
    zone smallint NOT NULL,
    number smallint NOT NULL,
    eligible_voters integer NOT NULL CHECK (eligible_voters > 0),
    key text GENERATED ALWAYS AS (
        state
        || '-' || lpad(municipality_code::text, 5, '0')
        || '-' || lpad(zone::text, 4, '0')
        || '-' || lpad(number::text, 4, '0')
    ) STORED PRIMARY KEY
);

CREATE INDEX sections_state_idx ON sections (state);

CREATE TABLE ballots (
    year smallint NOT NULL,
    round smallint NOT NULL,
    section text NOT NULL REFERENCES sections (key),
    blank_votes integer NOT NULL CHECK (blank_votes >= 0),
    null_votes integer NOT NULL CHECK (null_votes >= 0),
    issued_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    payload bytea NOT NULL,
    signature char(64) NOT NULL,
    PRIMARY KEY (year, round, section),
    FOREIGN KEY (year, round) REFERENCES elections
);

CREATE TABLE ballot_votes (
    year smallint NOT NULL,
    round smallint NOT NULL,
    section text NOT NULL,
    candidate smallint NOT NULL,
    votes integer NOT NULL CHECK (votes >= 0),
    PRIMARY KEY (year, round, section, candidate),
    FOREIGN KEY (year, round, section) REFERENCES ballots ON DELETE CASCADE,
    FOREIGN KEY (year, round, candidate) REFERENCES candidates
);
