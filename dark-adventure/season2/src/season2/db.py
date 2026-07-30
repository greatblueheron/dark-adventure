"""Supabase client + connectivity check.

Usage: python -m season2.db check
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def check() -> None:
    c = client()
    res = c.table("campaigns").select("id, name, status").execute()
    print(f"OK — connected. {len(res.data)} campaign(s) found.")
    for row in res.data:
        print(f"  {row['name']} [{row['status']}]")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check()
    else:
        print("Usage: python -m season2.db check")
