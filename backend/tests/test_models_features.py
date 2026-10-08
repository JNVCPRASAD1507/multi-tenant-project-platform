from sqlalchemy import inspect


def test_notification_comment_audit_chat_tables_exist(test_engine):
    tables = set(inspect(test_engine).get_table_names())
    expected = {
        "notifications",
        "comments",
        "audit_logs",
        "chat_rooms",
        "chat_participants",
        "chat_messages",
    }
    assert expected.issubset(tables)


def test_core_tenant_tables_exist(test_engine):
    tables = set(inspect(test_engine).get_table_names())
    expected = {
        "users",
        "roles",
        "organizations",
        "organization_members",
        "projects",
        "project_members",
        "tasks",
        "task_dependencies",
    }
    assert expected.issubset(tables)
