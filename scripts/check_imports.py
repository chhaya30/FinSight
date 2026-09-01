# scripts/check_imports.py

import importlib
import pkgutil

import app


failed_imports = []

for module in pkgutil.walk_packages(app.__path__, prefix="app."):
    try:
        importlib.import_module(module.name)
        print(f"✓ {module.name}")
    except Exception as error:
        failed_imports.append((module.name, str(error)))
        print(f"✗ {module.name}: {error}")


print("\n" + "=" * 60)
print("FAILED IMPORTS")
print("=" * 60)

for module, error in failed_imports:
    print(f"\n{module}")
    print(f"  {error}")

print(f"\nTotal failures: {len(failed_imports)}")