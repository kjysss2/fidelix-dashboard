#!/usr/bin/env python3
"""Refresh dashboard cache once; intended for scheduled runs."""

import json

from server import SERVICE


if __name__ == "__main__":
    result = SERVICE.refresh("daily-automation")
    print(json.dumps({
        "ok": result.get("ok"),
        "updatedSources": result.get("updatedSources", []),
        "errors": result.get("errors", []),
    }, ensure_ascii=False))
