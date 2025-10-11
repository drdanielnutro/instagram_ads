#!/usr/bin/env python3
"""
Imprime notificações no terminal e mantém compatibilidade ASCII.
"""
import json
import sys

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"[hooks] Notification inválida: {exc}", file=sys.stderr)
        return 0

    message = payload.get("message")
    if message:
        print(f"[Claude Code] NOTIFICATION: {message}")
    return 0

if __name__ == "__main__":
    sys.exit(main())