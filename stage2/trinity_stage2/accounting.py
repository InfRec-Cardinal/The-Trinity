import math
from uuid import uuid4

FIELDS = {"input": "input_tokens", "output": "output_tokens", "cachedInput": "cache_read_input_tokens", "cacheCreationInput": "cache_creation_input_tokens"}


def token_usage(raw):
    def read(key, alias):
        value = raw.get(key, raw.get(alias)) if isinstance(raw, dict) else getattr(raw, alias, None)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None
    usage = {key: read(key, alias) for key, alias in FIELDS.items()}
    if isinstance(raw, dict) and raw.get("partial"):
        usage["partial"] = True
    inputs = [usage[key] for key in ("input", "cachedInput", "cacheCreationInput")]
    usage["totalInput"] = sum(inputs) if all(value is not None for value in inputs) else None
    usage["total"] = usage["totalInput"] + usage["output"] if not usage.get("partial") and usage["totalInput"] is not None and usage["output"] is not None else None
    usage["knownTotalInput"] = sum(value for value in inputs if value is not None)
    usage["knownTotal"] = usage["knownTotalInput"] + (usage["output"] or 0)
    return usage


def model_call(records, failed, model):
    usage = {key: sum(row["usage"][key] for row in records) if all(row["usage"][key] is not None for row in records) else None for key in FIELDS}
    if any(row["usage"].get("partial") for row in records):
        usage["partial"] = True
    return {"callId": str(uuid4()), "model": model, "failed": failed, "usage": token_usage(usage), "attemptRecords": records, "unknownAttempts": 0}


def token_summary(calls):
    attempts = [row for call in calls for row in (call.get("attemptRecords") or [call])]
    usages = [token_usage(row.get("usage")) for row in attempts]
    unknown = sum(call.get("unknownAttempts", 0) for call in calls)
    result = {"calls": len(calls), "attempts": len(attempts) + unknown, "reportedCalls": sum((call.get("usage") or {}).get("input") is not None and (call.get("usage") or {}).get("output") is not None for call in calls), "failedCalls": sum(bool(call.get("failed")) for call in calls), "failedAttempts": sum(bool(row.get("failed")) for row in attempts), "partialAttempts": sum(bool(usage.get("partial")) for usage in usages), "unknownAttempts": unknown}
    for key in [*FIELDS, "totalInput", "total"]:
        values = [usage[key] for usage in usages]
        result[key] = {"known": sum(value for value in values if value is not None), "missingCalls": sum(token_usage(call.get("usage"))[key] is None for call in calls), "missingAttempts": sum(value is None for value in values) + unknown}
    result["totalInput"]["lowerBound"] = sum(usage["knownTotalInput"] for usage in usages)
    result["total"]["lowerBound"] = sum(usage["knownTotal"] for usage in usages)
    result["complete"] = result["total"]["missingAttempts"] == 0 and result["partialAttempts"] == 0
    result["exactTotal"] = result["total"]["known"] if result["complete"] else None
    return result
