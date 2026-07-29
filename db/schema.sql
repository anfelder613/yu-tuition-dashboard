-- YU Peer Tuition Dashboard — database schema
--
-- Auto-applied by the postgres container on first startup (mounted into
-- /docker-entrypoint-initdb.d/). Postgres is the authoritative store for the
-- IPEDS tuition facts; the Streamlit app queries it directly (no flat-file
-- reads baked into the app).
--
-- This file owns FACTS and CONSTRAINTS only. Presentation (colors, isYU,
-- display order) stays in the app layer — do not duplicate it here.
--
-- All six schools are private. There is no in-state/in-district tier for any
-- of them — only out-of-state / private-rate figures are stored.

CREATE TABLE institutions (
    key    text PRIMARY KEY,             -- 'yu', 'northeastern', ...
    name   text NOT NULL,
    unitid text NOT NULL UNIQUE          -- IPEDS UNITID (provenance only)
);

-- One row per institution / academic year / level. Tuition and required fees
-- stay in separate columns regardless of how they're eventually displayed —
-- see CLAUDE.md > Data Rules. academic_year is IPEDS's raw `year` value, the
-- START year of the academic year (confirmed against the IPEDS data
-- dictionary text, e.g. year=2024 covers "the full academic year 2024-25");
-- the app formats it as "2024-25" at display time.
CREATE TABLE tuition_fees (
    institution_key text NOT NULL REFERENCES institutions (key),
    academic_year   int  NOT NULL,
    level           text NOT NULL CHECK (level IN ('undergraduate', 'graduate')),
    tuition_usd     int  NOT NULL,
    fees_usd        int  NOT NULL,
    PRIMARY KEY (institution_key, academic_year, level)
);

-- Seed the six institutions (facts/constraints). Presentation lives in the app.
INSERT INTO institutions (key, name, unitid) VALUES
    ('yu',           'Yeshiva University',               '197708'),
    ('northeastern', 'Northeastern University',          '167358'),
    ('rpi',          'Rensselaer Polytechnic Institute', '194824'),
    ('miami',        'University of Miami',              '135726'),
    ('stevens',      'Stevens Institute of Technology',  '186867'),
    ('clarkson',     'Clarkson University',              '190044');
