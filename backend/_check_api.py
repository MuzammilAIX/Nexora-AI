import sys, json, urllib.request, urllib.error
for s in ["pending", "approved", "rejected", "executed"]:
    url = f"http://localhost:8000/api/v1/approvals?status={s}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode())
        print(f"status={s!r:12} -> HTTP {r.status}  count={len(data)}  ids={[x['id'][:8] for x in data]}")
    except urllib.error.HTTPError as e:
        print(f"status={s!r:12} -> HTTP {e.code}  body={e.read()[:200]!r}")
    except Exception as e:
        print(f"status={s!r:12} -> ERR {e!r}")
