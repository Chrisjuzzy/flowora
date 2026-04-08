import contextvars

_tenant_id_ctx = contextvars.ContextVar("tenant_id", default=None)


def set_current_tenant(tenant_id: int | None) -> None:
    _tenant_id_ctx.set(tenant_id)


def get_current_tenant() -> int | None:
    return _tenant_id_ctx.get()
