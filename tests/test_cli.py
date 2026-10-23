from filingpoint import create_app


def test_migrate_command_sets_up_a_fresh_database(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "cli.db")})
    runner = app.test_cli_runner()

    first = runner.invoke(args=["migrate"])
    assert first.exit_code == 0
    assert "Applied 0001_initial.sql" in first.output

    second = runner.invoke(args=["migrate"])
    assert second.exit_code == 0
    assert "Applied" not in second.output
    assert "Database is up to date." in second.output
