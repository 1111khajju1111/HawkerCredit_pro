import os
import sys

# Ensure backend/ is importable regardless of cwd pytest is invoked from.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Ensure scripts/ is importable so we can call the shared seeding routine.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')))


def pytest_configure(config):
    """
    Seeds the database with demo users/vendors before the test session starts.
    test_auth_login (and any future test hitting real endpoints) depends on
    known seed credentials existing; this makes `pytest` runnable standalone
    right after `pip install -r requirements.txt`, with no manual seeding step.
    """
    try:
        from generate_demo_data import generate_synthetic_dataset
        generate_synthetic_dataset()
    except Exception as e:
        # Don't hard-fail collection if seeding has an issue -- individual tests
        # that depend on seed data will fail with a clear assertion error instead,
        # which is easier to debug than a cryptic conftest crash.
        print(f"[conftest] WARNING: demo data seeding failed: {e}")
