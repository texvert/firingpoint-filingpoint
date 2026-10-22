-- =====================================================================
-- Filingpoint — database schema, v1 (v0.1 release)
-- SQLite 3.37+ (STRICT tables)
-- Licence: MIT
-- =====================================================================
--
-- DESIGN PRINCIPLES
--
-- 1. No PII. Users are User IDs. No names, contact details, ages
--    or body measurements are stored anywhere.
--
-- 2. Settings belong to the ASSET. Every settings change is a new,
--    append-only snapshot attached to a jacket or sling. Nothing is
--    edited in place. "Current settings" = newest snapshot;
--    "settings as of date X" = newest snapshot recorded before X.
--
-- 3. ONE personal link. A person is connected to settings only through
--    jacket_allocations.user_id. Blanking that one column
--    (manually, by the retention job, or automatically via
--    ON DELETE SET NULL) removes the person from every snapshot made
--    during that allocation. The asset keeps its history.
--
-- 4. Measurements are whole millimetres (INTEGER). The UI converts to
--    cm/inches. No floating-point rounding drift.
--
-- 5. Timestamps are ISO 8601 UTC text, e.g. '2026-10-22T09:30:00Z'.
--    ISO text sorts correctly as plain text, which SQLite relies on.
--
-- 6. Organisations exist from day one, and can be nested. v0.1 uses a
--    single organisation with no scoping logic; the columns are here so
--    that adding multi-organisation support later doesn't require
--    migrating every table.
--
-- REQUIRED ON EVERY CONNECTION
--
--    PRAGMA foreign_keys = ON;
--
-- SQLite ships with foreign keys OFF. Without this, REFERENCES clauses
-- are ignored and ON DELETE SET NULL silently does nothing, which
-- would break erasure. The app's connection helper must set it, and a
-- test must prove it.
-- =====================================================================

PRAGMA foreign_keys = ON;


-- ---------------------------------------------------------------------
-- ORGANISATIONS
-- A club or other organisation using this instance. parent_id allows
-- one organisation to sit within another (e.g. a section, branch or
-- affiliated group that shares the parent's venue or equipment).
-- parent_id is NULL for a top-level organisation.
-- ---------------------------------------------------------------------
CREATE TABLE organisations (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    parent_id   INTEGER REFERENCES organisations(id) ON DELETE RESTRICT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (parent_id IS NULL OR parent_id <> id)
) STRICT;


-- ---------------------------------------------------------------------
-- ADMINS
-- Administrator accounts, kept entirely separate from user accounts.
-- A person who is both has two logins. Admin actions elsewhere point
-- here via ON DELETE SET NULL, so removing an admin account doesn't
-- delete the history it recorded.
-- ---------------------------------------------------------------------
CREATE TABLE admins (
    id                        INTEGER PRIMARY KEY,
    organisation_id           INTEGER NOT NULL REFERENCES organisations(id) ON DELETE RESTRICT,
    username                  TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash             TEXT    NOT NULL,
    -- Recovery: an admin-issued temporary password forces a change on
    -- next login and stops working after it expires.
    must_change_password      INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
    temp_password_expires_at  TEXT,
    created_at                TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    disabled_at               TEXT
) STRICT;


-- ---------------------------------------------------------------------
-- USERS
-- The people equipment is allocated to (club members, or the owner in
-- a personal install). Admin accounts are a separate table.
-- User IDs (e.g. 'U014') are assigned by the system and never change.
-- Usernames are chosen by the user, can be changed, and are what other
-- people see; records always join on the User ID.
-- password_hash is NULL for a user who has no login.
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id                        TEXT    PRIMARY KEY,
    organisation_id           INTEGER NOT NULL REFERENCES organisations(id) ON DELETE RESTRICT,
    username                  TEXT    UNIQUE COLLATE NOCASE,
    password_hash             TEXT,
    must_change_password      INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
    temp_password_expires_at  TEXT,
    status                    TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at                TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (password_hash IS NULL OR username IS NOT NULL)
) STRICT;


-- ---------------------------------------------------------------------
-- JACKETS
-- Sizes follow common manufacturer conventions. All are optional,
-- since makers list different measurements.
-- closure_type and shoulder_strap_count describe what this jacket CAN
-- adjust; jacket_settings records where it IS adjusted.
-- notes: admin-only, asset condition (e.g. wear, alterations).
-- notes_reviewed supports a "submit for review" queue.
-- ownership = 'personal' is recorded but not otherwise tracked in v0.1.
-- ---------------------------------------------------------------------
CREATE TABLE jackets (
    id                    INTEGER PRIMARY KEY,
    organisation_id       INTEGER NOT NULL REFERENCES organisations(id) ON DELETE RESTRICT,
    club_number           TEXT    NOT NULL,
    make                  TEXT,
    model                 TEXT,
    size_label            TEXT,
    handedness            TEXT    NOT NULL CHECK (handedness IN ('L', 'R')),
    chest_mm              INTEGER CHECK (chest_mm > 0),
    waist_mm              INTEGER CHECK (waist_mm > 0),
    back_length_mm        INTEGER CHECK (back_length_mm > 0),
    outside_sleeve_mm     INTEGER CHECK (outside_sleeve_mm > 0),
    hip_mm                INTEGER CHECK (hip_mm > 0),
    closure_type          TEXT    NOT NULL DEFAULT 'buttons' CHECK (closure_type IN ('buttons', 'zip', 'straps')),
    shoulder_strap_count  INTEGER NOT NULL DEFAULT 1 CHECK (shoulder_strap_count IN (1, 2)),
    ownership             TEXT    NOT NULL DEFAULT 'club' CHECK (ownership IN ('club', 'personal')),
    condition             TEXT,
    notes                 TEXT,
    notes_reviewed        INTEGER NOT NULL DEFAULT 1 CHECK (notes_reviewed IN (0, 1)),
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    retired_at            TEXT,
    UNIQUE (organisation_id, club_number)
) STRICT;


-- ---------------------------------------------------------------------
-- SLINGS
-- hole_count varies by model, which is why sling hole numbers don't
-- translate between slings (see sling_settings.bicep_to_hook_mm).
-- ---------------------------------------------------------------------
CREATE TABLE slings (
    id               INTEGER PRIMARY KEY,
    organisation_id  INTEGER NOT NULL REFERENCES organisations(id) ON DELETE RESTRICT,
    club_number      TEXT    NOT NULL,
    make             TEXT,
    model            TEXT,
    hole_count       INTEGER CHECK (hole_count > 0),
    ownership        TEXT    NOT NULL DEFAULT 'club' CHECK (ownership IN ('club', 'personal')),
    condition        TEXT,
    notes            TEXT,
    notes_reviewed   INTEGER NOT NULL DEFAULT 1 CHECK (notes_reviewed IN (0, 1)),
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    retired_at       TEXT,
    UNIQUE (organisation_id, club_number)
) STRICT;


-- ---------------------------------------------------------------------
-- SLING PAIRINGS
-- Semi-permanent sling <-> jacket link, with history. end_at NULL
-- means "current". A sling follows its paired jacket on allocation.
-- The two partial unique indexes below enforce: at most one current
-- pairing per sling, and at most one per jacket.
-- ---------------------------------------------------------------------
CREATE TABLE sling_pairings (
    id                    INTEGER PRIMARY KEY,
    sling_id              INTEGER NOT NULL REFERENCES slings(id)  ON DELETE CASCADE,
    jacket_id             INTEGER NOT NULL REFERENCES jackets(id) ON DELETE CASCADE,
    start_at              TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    end_at                TEXT,
    changed_by_admin_id   INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    CHECK (end_at IS NULL OR end_at >= start_at)
) STRICT;

CREATE UNIQUE INDEX one_current_pairing_per_sling
    ON sling_pairings (sling_id)  WHERE end_at IS NULL;
CREATE UNIQUE INDEX one_current_pairing_per_jacket
    ON sling_pairings (jacket_id) WHERE end_at IS NULL;


-- ---------------------------------------------------------------------
-- JACKET ALLOCATIONS
-- Jacket <-> user, with history. THIS IS THE ONLY PLACE A PERSON IS
-- LINKED TO EQUIPMENT DATA.
--
-- user_id ON DELETE SET NULL: deleting a user (e.g. an erasure
-- request, or a member leaving) blanks every link at once.
--
-- Lifecycle of a returned jacket (end_at set):
--   end_at + 14 days   user can still see and export it, with an
--                      in-app notice; after that it's hidden from them
--                      (derived from end_at, no extra column needed)
--   end_at + 6 months  retention job coarsens timestamps on this
--                      allocation and its snapshots to the month;
--                      coarsened_at records that it ran
--   end_at + 12 months retention job sets user_id = NULL;
--                      unlinked_at records that it ran
-- Periods are app configuration (defaults above), not hard-coded here.
--
-- reason: pick-list, to keep free text (and stray names) out.
-- Several open allocations on one jacket = a shared jacket.
-- ---------------------------------------------------------------------
CREATE TABLE jacket_allocations (
    id                    INTEGER PRIMARY KEY,
    jacket_id             INTEGER NOT NULL REFERENCES jackets(id) ON DELETE CASCADE,
    user_id            TEXT    REFERENCES users(id) ON DELETE SET NULL,
    start_at              TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    end_at                TEXT,
    reason                TEXT    NOT NULL CHECK (reason IN ('new_member', 'swap', 'temporary_loan', 'returned', 'other')),
    reason_note           TEXT,
    reason_note_reviewed  INTEGER NOT NULL DEFAULT 1 CHECK (reason_note_reviewed IN (0, 1)),
    changed_by_admin_id   INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    coarsened_at          TEXT,
    unlinked_at           TEXT,
    CHECK (end_at IS NULL OR end_at >= start_at)
) STRICT;

CREATE INDEX jacket_allocations_by_user ON jacket_allocations (user_id);
CREATE INDEX jacket_allocations_by_jacket  ON jacket_allocations (jacket_id);


-- ---------------------------------------------------------------------
-- JACKET SETTINGS (append-only snapshots)
-- One row per change; each row is a complete snapshot, with its straps
-- and buttons in the child tables below.
--
-- allocation_id links the snapshot to a person indirectly. NULL means
-- the jacket's default/baseline setup, not tied to anyone.
--
-- Order: after coarsening, several snapshots can share the same month
-- timestamp. Sort by recorded_at, then id; ids only ever increase, so
-- the original order is kept.
-- ---------------------------------------------------------------------
CREATE TABLE jacket_settings (
    id                      INTEGER PRIMARY KEY,
    jacket_id               INTEGER NOT NULL REFERENCES jackets(id) ON DELETE CASCADE,
    allocation_id           INTEGER REFERENCES jacket_allocations(id) ON DELETE SET NULL,
    recorded_at             TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    sling_height_position   INTEGER CHECK (sling_height_position > 0),
    notes                   TEXT,
    notes_reviewed          INTEGER NOT NULL DEFAULT 1 CHECK (notes_reviewed IN (0, 1)),
    recorded_by_admin_id    INTEGER REFERENCES admins(id) ON DELETE SET NULL
) STRICT;

CREATE INDEX jacket_settings_by_jacket_time ON jacket_settings (jacket_id, recorded_at, id);
CREATE INDEX jacket_settings_by_allocation  ON jacket_settings (allocation_id);

-- Shoulder strap tension, in holes. One row per strap (1, or 2 on
-- jackets with a double strap).
CREATE TABLE jacket_setting_straps (
    setting_id    INTEGER NOT NULL REFERENCES jacket_settings(id) ON DELETE CASCADE,
    strap_index   INTEGER NOT NULL CHECK (strap_index IN (1, 2)),
    hole          INTEGER NOT NULL CHECK (hole > 0),
    PRIMARY KEY (setting_id, strap_index)
) STRICT;

-- Buttons fitted. The number of rows IS the button count (0-5); a
-- zip- or strap-closed jacket has no rows here.
-- button_index runs from the bottom up.
CREATE TABLE jacket_setting_buttons (
    setting_id      INTEGER NOT NULL REFERENCES jacket_settings(id) ON DELETE CASCADE,
    button_index    INTEGER NOT NULL CHECK (button_index BETWEEN 1 AND 5),
    height_mm       INTEGER NOT NULL CHECK (height_mm >= 0),
    edge_offset_mm  INTEGER NOT NULL CHECK (edge_offset_mm >= 0),
    PRIMARY KEY (setting_id, button_index)
) STRICT;


-- ---------------------------------------------------------------------
-- SLING SETTINGS (append-only snapshots)
-- hole: quick setting, meaningful only on this sling.
-- bicep_to_hook_mm: portable measurement, carries across slings with
-- different hole counts. At least one of the two must be recorded.
-- allocation_id is the allocation of the jacket this sling was paired
-- with at the time, so the same single link covers sling data too.
-- ---------------------------------------------------------------------
CREATE TABLE sling_settings (
    id                    INTEGER PRIMARY KEY,
    sling_id              INTEGER NOT NULL REFERENCES slings(id) ON DELETE CASCADE,
    allocation_id         INTEGER REFERENCES jacket_allocations(id) ON DELETE SET NULL,
    recorded_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    hole                  INTEGER CHECK (hole > 0),
    bicep_to_hook_mm      INTEGER CHECK (bicep_to_hook_mm > 0),
    notes                 TEXT,
    notes_reviewed        INTEGER NOT NULL DEFAULT 1 CHECK (notes_reviewed IN (0, 1)),
    recorded_by_admin_id  INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    CHECK (hole IS NOT NULL OR bicep_to_hook_mm IS NOT NULL)
) STRICT;

CREATE INDEX sling_settings_by_sling_time  ON sling_settings (sling_id, recorded_at, id);
CREATE INDEX sling_settings_by_allocation  ON sling_settings (allocation_id);


-- ---------------------------------------------------------------------
-- SCHEMA VERSION
-- Migrations are numbered SQL files (0002_*.sql, ...). The runner
-- compares this number with the files and applies the newer ones.
-- ---------------------------------------------------------------------
PRAGMA user_version = 1;
