"""End-to-end test for /api/team/* and /api/audit."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

BASE = "http://127.0.0.1:8000/api"

# Fill these in from an existing user. If you don't know the password,
# register a fresh user in the same tenant via /api/auth/register first.
EMAIL = input("Login email: ").strip()
PASSWORD = input("Password: ").strip()


async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        # 1. Login
        r = await c.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        print(f"\n[1] login: {r.status_code}")
        if r.status_code != 200:
            print(r.text)
            return
        token = r.json().get("access_token") or r.json().get("token")
        if not token:
            print("no access_token in response:", r.json())
            return
        H = {"Authorization": f"Bearer {token}"}
        print(f"    token: {token[:20]}...")

        # 2. GET /team/members
        r = await c.get(f"{BASE}/team/members", headers=H)
        print(f"\n[2] GET /team/members: {r.status_code}")
        print(json.dumps(r.json(), indent=2)[:600])

        # 3. GET /team/roles
        r = await c.get(f"{BASE}/team/roles", headers=H)
        print(f"\n[3] GET /team/roles: {r.status_code}")
        roles = r.json()
        print(f"    {len(roles)} roles")
        for role in roles:
            print(f"      - {role['name']:<10} system={role['is_system']}  id={role['id']}")

        # Find the 'manager' role id for the invite below
        manager_role = next((x for x in roles if x["name"] == "manager"), None)
        if not manager_role:
            print("    FATAL: manager role missing — roles seed failed")
            return
        manager_id = manager_role["id"]

        # 4. GET /team/invitations (before)
        r = await c.get(f"{BASE}/team/invitations", headers=H)
        print(f"\n[4] GET /team/invitations (before): {r.status_code}, count={len(r.json())}")

        # 5. POST /team/invite
        r = await c.post(
            f"{BASE}/team/invite",
            headers=H,
            json={"email": "newperson@example.com", "role_id": manager_id},
        )
        print(f"\n[5] POST /team/invite: {r.status_code}")
        print(json.dumps(r.json(), indent=2)[:400])

        # 6. GET /team/invitations (after)
        r = await c.get(f"{BASE}/team/invitations", headers=H)
        print(f"\n[6] GET /team/invitations (after): {r.status_code}, count={len(r.json())}")

        # 7. GET /audit — look for team.invited
        r = await c.get(f"{BASE}/audit?event_type=team.invited&limit=10", headers=H)
        print(f"\n[7] GET /audit?event_type=team.invited: {r.status_code}")
        events = r.json()
        print(f"    {len(events)} events")
        for e in events[:3]:
            print(f"      - {e['event_type']}  subject={e['subject_id']}  at={e['created_at']}")

        # 8. Permission denial test — try invite without a permission
        # (only meaningful if your logged-in user is NOT owner/admin)
        print(f"\n[8] (manual) if your user is operator/viewer, expect 403 on POST /team/invite above")

asyncio.run(main())
