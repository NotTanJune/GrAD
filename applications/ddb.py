# applications/ddb.py
import os
import datetime
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    EndpointConnectionError,
    BotoCoreError,
)

REGION = os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1")
TABLE = os.getenv("APPMGR_DDB_TABLE", "emergency-hackathon")

# -------- feature toggle / availability checks --------


def _ddb_enabled() -> bool:
    # Only try DynamoDB if we have credentials and a table name
    return bool(
        TABLE and os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
    )


def _now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _to_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


_ddb = None
_tbl = None


def _get_tbl():
    global _ddb, _tbl
    if not _ddb:
        _ddb = boto3.resource("dynamodb", region_name=REGION)
    if not _tbl:
        _tbl = _ddb.Table(TABLE)
    return _tbl


def _safe_ddb(call, *, default=None):
    """
    Run a DynamoDB call but swallow infra/credential issues and return 'default'.
    This prevents production 500s when AWS isn’t configured on the host.
    """
    if not _ddb_enabled():
        return default
    try:
        return call()
    except (
        NoCredentialsError,
        EndpointConnectionError,
        ClientError,
        BotoCoreError,
        Exception,
    ):
        return default


def get_all_states(username: str) -> Dict[str, Dict[str, Any]]:
    """Return { '<app_id>': {status, priority, updated_at}, ... } or {}."""

    def _do():
        tbl = _get_tbl()
        resp = tbl.get_item(Key={"username": username})
        item = resp.get("Item") or {}
        return item.get("apps", {}) or {}

    return _safe_ddb(_do, default={})  # fail-soft


def get_state(username: str, app_id: int) -> Optional[Dict[str, Any]]:
    return get_all_states(username).get(str(app_id))


def upsert_app_map(username: str, app_id: int, *, status: str, priority: int) -> None:
    """
    Safely set apps.<app_id> = {status, priority, updated_at}.
    If the 'apps' map doesn’t exist or is bad type, repair and retry once.
    If DDB is disabled/unavailable, this is a no-op.
    """
    if not _ddb_enabled():
        return

    def _set_child():
        tbl = _get_tbl()
        tbl.update_item(
            Key={"username": username},
            UpdateExpression="SET #apps.#aid = :val, updated_at = :t",
            ExpressionAttributeNames={"#apps": "apps", "#aid": str(app_id)},
            ExpressionAttributeValues={
                ":val": {
                    "status": status,
                    "priority": int(priority),
                    "updated_at": _now(),
                },
                ":t": _now(),
            },
        )

    def _do():
        try:
            _set_child()
        except ClientError as e:
            msg = e.response.get("Error", {}).get("Message", "")
            # Repair the parent map then retry once
            if (
                "document path" in msg
                or "invalid for update" in msg
                or "path" in msg.lower()
            ):
                tbl = _get_tbl()
                tbl.update_item(
                    Key={"username": username},
                    UpdateExpression="SET #apps = :empty, updated_at = :t",
                    ExpressionAttributeNames={"#apps": "apps"},
                    ExpressionAttributeValues={":empty": {}, ":t": _now()},
                )
                _set_child()
            else:
                raise

    _safe_ddb(_do, default=None)


def put_state(username: str, app_id: int, status: str, priority: int) -> None:
    upsert_app_map(username, app_id, status=status, priority=priority)


def update_status(
    username: str, app_id: int, status: str, *, priority: Optional[int] = None
) -> None:
    cur = get_state(username, app_id) or {}
    pri = _to_int(cur.get("priority", 999) if priority is None else priority, 999)
    upsert_app_map(username, app_id, status=status, priority=pri)


def update_priority(username: str, app_id: int, priority: int) -> None:
    cur = get_state(username, app_id) or {}
    st = str(cur.get("status", "submitted"))
    upsert_app_map(username, app_id, status=st, priority=int(priority))


def delete_state(username: str, app_id: int) -> None:
    if not _ddb_enabled():
        return

    def _do():
        tbl = _get_tbl()
        tbl.update_item(
            Key={"username": username},
            UpdateExpression="REMOVE #apps.#aid SET updated_at = :t",
            ExpressionAttributeNames={"#apps": "apps", "#aid": str(app_id)},
            ExpressionAttributeValues={":t": _now()},
        )

    _safe_ddb(_do, default=None)


def overlay_states(username: str, app_objs: list) -> None:
    """
    Overlay DynamoDB values onto Django Application objects in-place for rendering.
    If DDB unavailable, this is effectively a no-op.
    """
    states = get_all_states(username)
    if not states:
        return
    for a in app_objs:
        st = states.get(str(a.id))
        if not st:
            continue
        if "status" in st:
            a.status = st["status"]
        if "priority" in st:
            try:
                a.priority = int(st["priority"])
            except Exception:
                pass
