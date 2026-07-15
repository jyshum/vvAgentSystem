import json
from contextlib import AbstractContextManager
from pathlib import Path

import pytest

from scripts.reset_client_data import (
    BACKUP_SQL,
    DELETE_ORDER,
    DELETE_SQL,
    GENERATED_TABLES,
    PRESERVED_TABLES,
    ResetVerificationError,
    parse_args,
    run_reset,
)


CLIENT_ID = "11111111-1111-4111-8111-111111111111"


def test_execute_requires_matching_confirmation(tmp_path):
    with pytest.raises(SystemExit, match="confirmation"):
        parse_args(
            [
                "--client-id",
                CLIENT_ID,
                "--backup-dir",
                str(tmp_path),
                "--execute",
                "--confirm-client-id",
                "wrong",
            ]
        )


def test_dry_run_is_the_default(tmp_path):
    args = parse_args(
        ["--client-id", CLIENT_ID, "--backup-dir", str(tmp_path)]
    )

    assert args.execute is False


def test_delete_order_is_foreign_key_safe():
    assert DELETE_ORDER == (
        "technical_audit_runs",
        "improvement_runs",
        "reports",
        "tracker_runs",
        "pipeline_runs",
    )


def test_preserved_tables_are_never_deleted():
    sql = "\n".join(DELETE_SQL.values()).lower()
    assert "delete from public.clients" not in sql
    assert "delete from public.queries" not in sql
    assert "delete from public.client_users" not in sql
    assert "delete from auth.users" not in sql


def test_every_query_is_client_scoped_and_parameterized():
    assert set(BACKUP_SQL) == set(PRESERVED_TABLES + GENERATED_TABLES)
    for sql in (*BACKUP_SQL.values(), *DELETE_SQL.values()):
        assert "%(client_id)s" in sql
        assert CLIENT_ID not in sql


@pytest.mark.parametrize(
    ("table", "owner"),
    [
        ("tracker_results", "tracker_runs"),
        ("prompt_scores", "tracker_runs"),
        ("competitive_gaps", "tracker_runs"),
        ("technical_audit_observations", "technical_audit_runs"),
        ("technical_audit_results", "technical_audit_runs"),
        ("page_inventory", "improvement_runs"),
        ("query_page_matches", "improvement_runs"),
        ("page_citation_scores", "improvement_runs"),
        ("action_cards", "improvement_runs"),
    ],
)
def test_child_backups_follow_their_generated_parent(table, owner):
    sql = BACKUP_SQL[table].lower()
    assert f"join public.{owner}" in sql
    assert f"{owner}.client_id = %(client_id)s" in sql


def test_auth_backup_projection_excludes_credentials_and_secret_values():
    sql = BACKUP_SQL["auth_users"].lower()
    for secret_column in (
        "encrypted_password",
        "confirmation_token",
        "recovery_token",
        "email_change_token",
        "reauthentication_token",
        "phone_change_token",
        "raw_app_meta_data",
        "raw_user_meta_data",
    ):
        assert secret_column not in sql


class FakeCursor(AbstractContextManager):
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params):
        self.connection.calls.append((sql, params))
        table = self.connection.table_for_sql(sql)
        if sql.lstrip().lower().startswith("delete"):
            self.connection.deleted.add(table)
            self.rows = []
            return

        if table in GENERATED_TABLES and self.connection.deleted:
            self.rows = self.connection.post_delete_rows.get(table, [])
        else:
            call_number = self.connection.select_counts.get(table, 0)
            self.connection.select_counts[table] = call_number + 1
            versions = self.connection.rows.get(table, [[]])
            self.rows = versions[min(call_number, len(versions) - 1)]

    def fetchall(self):
        return self.rows


class FakeTransaction(AbstractContextManager):
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.connection.transaction_entries += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.connection.commits += 1
        else:
            self.connection.rollbacks += 1
        return False


class FakeConnection(AbstractContextManager):
    def __init__(self, rows=None, post_delete_rows=None):
        self.rows = rows or sample_rows()
        self.post_delete_rows = post_delete_rows or {}
        self.calls = []
        self.deleted = set()
        self.select_counts = {}
        self.transaction_entries = 0
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True
        return False

    def cursor(self):
        return FakeCursor(self)

    def transaction(self):
        return FakeTransaction(self)

    @staticmethod
    def table_for_sql(sql):
        normalized = " ".join(sql.lower().split())
        for table, query in BACKUP_SQL.items():
            if normalized == " ".join(query.lower().split()):
                return table
        for table, query in DELETE_SQL.items():
            if normalized == " ".join(query.lower().split()):
                return table
        raise AssertionError(f"Unexpected SQL: {sql}")


class ConnectRecorder:
    def __init__(self, connection):
        self.connection = connection
        self.calls = []

    def __call__(self, db_url, **kwargs):
        self.calls.append((db_url, kwargs))
        return self.connection


def sample_rows():
    rows = {
        "clients": [[{"id": CLIENT_ID, "name": "Example"}]],
        "queries": [[{"id": "query-1", "client_id": CLIENT_ID}]],
        "client_users": [
            [{"id": "access-1", "client_id": CLIENT_ID, "user_id": "user-1"}]
        ],
        "auth_users": [[{"id": "user-1", "role": "authenticated"}]],
    }
    for table in GENERATED_TABLES:
        rows[table] = [[{"id": f"{table}-1"}]]
    return rows


def parsed_args(tmp_path, *, execute=False):
    argv = ["--client-id", CLIENT_ID, "--backup-dir", str(tmp_path)]
    if execute:
        argv.extend(["--execute", "--confirm-client-id", CLIENT_ID])
    return parse_args(argv)


def read_json_files(directory):
    return {
        path.name: json.loads(path.read_text())
        for path in Path(directory).glob("*.json")
    }


def test_dry_run_exports_all_tables_without_write_transaction_or_deletes(tmp_path):
    connection = FakeConnection()
    connect = ConnectRecorder(connection)

    report = run_reset(
        parsed_args(tmp_path), db_url="postgresql://not-a-secret", connect=connect
    )

    assert connect.calls[0][1]["autocommit"] is True
    assert connection.transaction_entries == 0
    assert connection.deleted == set()
    assert report["status"] == "dry_run_complete"
    files = read_json_files(tmp_path)
    expected = {
        *(f"{table}.json" for table in PRESERVED_TABLES + GENERATED_TABLES),
        "manifest.json",
        "verification.json",
    }
    assert set(files) == expected
    assert files["manifest.json"]["generated_counts"] == {
        table: 1 for table in GENERATED_TABLES
    }


def test_execute_deletes_only_parent_ownership_in_one_transaction(tmp_path):
    connection = FakeConnection()
    connect = ConnectRecorder(connection)

    report = run_reset(
        parsed_args(tmp_path, execute=True),
        db_url="postgresql://not-a-secret",
        connect=connect,
    )

    delete_calls = [
        (sql, params)
        for sql, params in connection.calls
        if sql.lstrip().lower().startswith("delete")
    ]
    assert [FakeConnection.table_for_sql(sql) for sql, _ in delete_calls] == list(
        DELETE_ORDER
    )
    assert all(params == {"client_id": CLIENT_ID} for _, params in delete_calls)
    assert connect.calls[0][1]["autocommit"] is False
    assert connection.transaction_entries == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert report["status"] == "verified"
    assert report["after_generated_counts"] == {
        table: 0 for table in GENERATED_TABLES
    }


def test_missing_client_aborts_before_any_delete(tmp_path):
    rows = sample_rows()
    rows["clients"] = [[]]
    connection = FakeConnection(rows=rows)

    with pytest.raises(ResetVerificationError, match="exactly one client"):
        run_reset(
            parsed_args(tmp_path, execute=True),
            db_url="postgresql://not-a-secret",
            connect=ConnectRecorder(connection),
        )

    assert connection.deleted == set()
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_generated_count_mismatch_rolls_back_transaction(tmp_path):
    connection = FakeConnection(
        post_delete_rows={"tracker_results": [{"id": "unexpected"}]}
    )

    with pytest.raises(ResetVerificationError, match="tracker_results"):
        run_reset(
            parsed_args(tmp_path, execute=True),
            db_url="postgresql://not-a-secret",
            connect=ConnectRecorder(connection),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_preserved_byte_mismatch_rolls_back_transaction(tmp_path):
    rows = sample_rows()
    rows["queries"] = [
        [{"id": "query-1", "client_id": CLIENT_ID}],
        [{"id": "query-1", "client_id": CLIENT_ID, "status": "changed"}],
    ]
    connection = FakeConnection(rows=rows)

    with pytest.raises(ResetVerificationError, match="queries"):
        run_reset(
            parsed_args(tmp_path, execute=True),
            db_url="postgresql://not-a-secret",
            connect=ConnectRecorder(connection),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_artifacts_never_serialize_database_url_or_secret_marker(tmp_path):
    rows = sample_rows()
    rows["auth_users"] = [[{"id": "user-1", "role": "authenticated"}]]
    database_url = "postgresql://user:SECRET_MARKER@db.example/database"

    run_reset(
        parsed_args(tmp_path),
        db_url=database_url,
        connect=ConnectRecorder(FakeConnection(rows=rows)),
    )

    serialized = "\n".join(path.read_text() for path in tmp_path.glob("*.json"))
    assert database_url not in serialized
    assert "SECRET_MARKER" not in serialized
