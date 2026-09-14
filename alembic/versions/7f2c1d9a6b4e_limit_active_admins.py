"""enforce maximum active admin accounts

Revision ID: 7f2c1d9a6b4e
Revises: 4b16a30a325d
"""

from alembic import op


revision = "7f2c1d9a6b4e"
down_revision = "4b16a30a325d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION enforce_active_admin_limit() RETURNS trigger AS $$
            DECLARE active_admin_count integer;
            BEGIN
                IF NEW.role = 'admin' AND NEW.is_active THEN
                    PERFORM pg_advisory_xact_lock(2147483647);
                    SELECT count(*) INTO active_admin_count
                    FROM users
                    WHERE role = 'admin'
                      AND is_active
                      AND id <> COALESCE(NEW.id, -1);
                    IF active_admin_count >= 2 THEN
                        RAISE EXCEPTION 'maximum of two active admin accounts exceeded';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER users_active_admin_limit
            BEFORE INSERT OR UPDATE OF role, is_active ON users
            FOR EACH ROW EXECUTE FUNCTION enforce_active_admin_limit();
            """
        )
    elif bind.dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER users_active_admin_limit_insert
            BEFORE INSERT ON users
            WHEN NEW.role = 'admin' AND NEW.is_active = 1
                 AND (SELECT count(*) FROM users WHERE role = 'admin' AND is_active = 1) >= 2
            BEGIN
                SELECT RAISE(ABORT, 'maximum of two active admin accounts exceeded');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER users_active_admin_limit_update
            BEFORE UPDATE OF role, is_active ON users
            WHEN NEW.role = 'admin' AND NEW.is_active = 1
                 AND (SELECT count(*) FROM users WHERE role = 'admin' AND is_active = 1 AND id <> OLD.id) >= 2
            BEGIN
                SELECT RAISE(ABORT, 'maximum of two active admin accounts exceeded');
            END;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS users_active_admin_limit ON users")
        op.execute("DROP FUNCTION IF EXISTS enforce_active_admin_limit()")
    elif bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS users_active_admin_limit_update")
        op.execute("DROP TRIGGER IF EXISTS users_active_admin_limit_insert")
