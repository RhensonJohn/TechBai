"""Start the TechBai system:  python main.py   ->  http://localhost:5000"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import app as backend  # noqa: E402

if __name__ == "__main__":
    print("\nTechBai is running -> http://localhost:5000")
    if backend.GENERATED_PASSWORD:
        print(f"Admin page: http://localhost:5000/admin.html\n"
              f"Admin password (random this run; set ADMIN_PASSWORD to keep one): "
              f"{backend.ADMIN_PASSWORD}\n")
    backend.app.run(host=os.environ.get("HOST", "127.0.0.1"),
                    port=int(os.environ.get("PORT", 5000)), debug=False)
