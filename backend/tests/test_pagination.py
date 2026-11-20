from sqlalchemy.dialects import postgresql

from app.api.admin import audit_log


class _Scalars:
    def all(self):
        return []


class _Result:
    def scalars(self):
        return _Scalars()


class _CaptureSession:
    async def execute(self, statement):
        self.statement = statement
        return _Result()


async def test_audit_log_applies_server_side_limit_and_offset():
    session = _CaptureSession()

    await audit_log(limit=51, offset=100, session=session)
    sql = str(
        session.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    assert "LIMIT 51 OFFSET 100" in sql
