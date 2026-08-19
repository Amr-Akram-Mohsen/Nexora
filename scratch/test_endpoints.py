import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core import create_app

def run_tests():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    client = app.test_client()

    endpoints_to_test = [
        # Public & Content Pages
        ("/", 200, "Home page"),
        ("/login", 200, "Login page"),
        ("/register", 200, "Register page"),
        ("/forgot-password", 200, "Forgot password page"),
        ("/about", 200, "About page"),
        ("/contact", 200, "Contact page"),
        ("/privacy", 200, "Privacy policy"),
        ("/terms", 200, "Terms of service"),
        ("/search?query=test", 200, "Search page"),
        ("/deals", 200, "Deals page"),
        # Admin Protected Endpoints (Protected by 401/403/302 guard when unauthenticated)
        ("/admin/users/", (401, 302), "Admin users guard"),
        ("/admin/contents/", (401, 302), "Admin contents guard"),
        ("/admin/scraping/control", (200, 401, 302), "Admin scraping control"),
    ]

    print(f"Testing {len(endpoints_to_test)} key routes with Flask test client...")
    passed = 0
    failed = 0

    with app.app_context():
        for url, expected_status, name in endpoints_to_test:
            expected = (expected_status,) if isinstance(expected_status, int) else expected_status
            try:
                resp = client.get(url)
                if resp.status_code in expected:
                    print(f"  [PASS] {name} ({url}) -> Status {resp.status_code}")
                    passed += 1
                else:
                    print(f"  [FAIL] {name} ({url}) -> Status {resp.status_code} (Expected {expected_status})")
                    failed += 1
            except Exception as e:
                print(f"  [ERROR] {name} ({url}) -> Exception: {e}")
                failed += 1

    print("\n------------------------------------------------")
    print(f"Endpoint test results: {passed} passed, {failed} failed out of {len(endpoints_to_test)} tested.")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
