def test_foreign_keys_are_enforced(db):
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_deleting_user_unlinks_allocations_but_keeps_history(db):
    db.execute("INSERT INTO organisations (name) VALUES ('Test Club')")
    db.execute("INSERT INTO users (id, organisation_id) VALUES ('U001', 1)")
    db.execute(
        "INSERT INTO jackets (organisation_id, club_number, handedness) "
        "VALUES (1, 'J01', 'R')"
    )
    db.execute(
        "INSERT INTO jacket_allocations (jacket_id, user_id, reason) "
        "VALUES (1, 'U001', 'new_member')"
    )
    db.execute("INSERT INTO jacket_settings (jacket_id, allocation_id) VALUES (1, 1)")

    db.execute("DELETE FROM users WHERE id = 'U001'")

    allocation = db.execute("SELECT user_id FROM jacket_allocations").fetchone()
    assert allocation["user_id"] is None

    snapshots = db.execute("SELECT COUNT(*) FROM jacket_settings").fetchone()[0]
    assert snapshots == 1
