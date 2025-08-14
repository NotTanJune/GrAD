# applications/ddb.py
import os
import datetime
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

REGION = os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1")
TABLE = os.getenv("APPMGR_DDB_TABLE", "emergency-hackathon")  # PK: username (S)

_ddb = boto3.resource("dynamodb", region_name=REGION)
_tbl = _ddb.Table(TABLE)


def _now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _to_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def get_all_states(username: str) -> Dict[str, Dict[str, Any]]:
    """Return { '<app_id>': {status, priority, updated_at}, ... } or {}."""
    resp = _tbl.get_item(Key={"username": username})
    item = resp.get("Item") or {}
    apps = item.get("apps") or {}
    return apps if isinstance(apps, dict) else {}


def get_state(username: str, app_id: int) -> Optional[Dict[str, Any]]:
    return get_all_states(username).get(str(app_id))


def upsert_app_map(username: str, app_id: int, *, status: str, priority: int) -> None:
    """
    Safely set apps.<app_id> = {status, priority, updated_at}.
    If 'apps' is missing/not a map, we create it first, then set the child.
    """

    def _set_child():
        _tbl.update_item(
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

    try:
        _set_child()
    except ClientError as e:
        msg = (e.response.get("Error", {}) or {}).get("Message", "").lower()
        if "document path" in msg or "invalid for update" in msg or "path" in msg:
            _tbl.update_item(
                Key={"username": username},
                UpdateExpression="SET #apps = if_not_exists(#apps, :empty), updated_at = :t",
                ExpressionAttributeNames={"#apps": "apps"},
                ExpressionAttributeValues={":empty": {}, ":t": _now()},
            )
            _set_child()
        else:
            raise


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
    st = str(cur.get("status", "SUBMITTED"))  # default normalized
    upsert_app_map(username, app_id, status=st, priority=int(priority))


def delete_state(username: str, app_id: int) -> None:
    """
    Remove apps.<app_id> if present; otherwise no-op.
    Always touches updated_at. Guard with a condition to avoid ValidationException.
    """
    names = {"#apps": "apps", "#aid": str(app_id)}
    try:
        _tbl.update_item(
            Key={"username": username},
            UpdateExpression="REMOVE #apps.#aid SET updated_at = :t",
            ConditionExpression="attribute_exists(#apps) AND attribute_exists(#apps.#aid)",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues={":t": _now()},
        )
    except ClientError as e:
        code = (e.response.get("Error", {}) or {}).get("Code")
        if code != "ConditionalCheckFailedException":
            raise
        _tbl.update_item(
            Key={"username": username},
            UpdateExpression="SET updated_at = :t",
            ExpressionAttributeValues={":t": _now()},
        )


def overlay_states(username: str, app_objs: list) -> None:
    """
    Overlay DynamoDB values onto Django Application objects in-place for rendering.
    """
    states = get_all_states(username)
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
