import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate-limiter instance, keyed by client IP. In-memory storage
# (slowapi's default) is fine for a single-process demo deployment but
# does NOT share state across multiple worker processes/instances - for a
# real multi-instance production deployment this should be backed by
# Redis (slowapi supports this via `storage_uri`). Documented here rather
# than silently assumed.
#
# Disabled automatically when RATE_LIMIT_ENABLED=false (the test suite
# sets this): the test client reuses one "IP" across dozens of requests
# per test run, so real per-minute limits would make the test suite
# itself look like abuse and start failing on request count alone rather
# than on actual behavior.
_rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "no")

limiter = Limiter(key_func=get_remote_address, enabled=_rate_limit_enabled)
