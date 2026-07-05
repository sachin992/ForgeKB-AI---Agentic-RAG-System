import time
from collections import defaultdict, deque

WINDOW_SECONDS = 60
LIMIT_PER_MINUTE = 30

_bucket: dict[str, deque[float]] = defaultdict(deque)


def allow_request(key: str, limit: int = LIMIT_PER_MINUTE, window: int = WINDOW_SECONDS) -> bool:
    now = time.time()
    q = _bucket[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True
