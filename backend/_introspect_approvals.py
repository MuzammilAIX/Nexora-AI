import app.routes.approvals as m
public = [n for n in dir(m) if not n.startswith("__")]
print("NAMES:")
for n in public:
    obj = getattr(m, n)
    kind = type(obj).__name__
    print(f"  {n}  ({kind})")
