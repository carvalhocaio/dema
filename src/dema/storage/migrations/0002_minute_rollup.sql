CREATE TABLE minute_totals (
    year smallint NOT NULL,
    round smallint NOT NULL,
    minute timestamptz NOT NULL,
    sections integer NOT NULL CHECK (sections >= 0),
    electorate bigint NOT NULL CHECK (electorate >= 0),
    blank_votes bigint NOT NULL CHECK (blank_votes >= 0),
    null_votes bigint NOT NULL CHECK (null_votes >= 0),
    PRIMARY KEY (year, round, minute),
    FOREIGN KEY (year, round) REFERENCES elections
);

CREATE TABLE minute_votes (
    year smallint NOT NULL,
    round smallint NOT NULL,
    minute timestamptz NOT NULL,
    candidate smallint NOT NULL,
    votes bigint NOT NULL CHECK (votes >= 0),
    PRIMARY KEY (year, round, minute, candidate),
    FOREIGN KEY (year, round, candidate) REFERENCES candidates
);

INSERT INTO minute_totals
    (year, round, minute, sections, electorate, blank_votes, null_votes)
SELECT
    b.year, b.round, date_trunc('minute', b.issued_at, 'UTC'),
    count(*), sum(s.eligible_voters), sum(b.blank_votes), sum(b.null_votes)
FROM ballots AS b
JOIN sections AS s ON s.key = b.section
GROUP BY 1, 2, 3;

INSERT INTO minute_votes (year, round, minute, candidate, votes)
SELECT v.year, v.round, date_trunc('minute', b.issued_at, 'UTC'), v.candidate, sum(v.votes)
FROM ballot_votes AS v
JOIN ballots AS b USING (year, round, section)
GROUP BY 1, 2, 3, 4;
