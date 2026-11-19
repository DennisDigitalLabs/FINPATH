import hmac
import math
import time
from collections import OrderedDict, deque
from threading import Lock

from backend.config import get_settings


class AuthRateLimiter:
	"""Process-local sliding-window limiter keyed by a secret-derived identifier."""

	MAX_BUCKETS = 10_000

	def __init__(self) -> None:
		self._attempts: OrderedDict[bytes, deque[float]] = OrderedDict()
		self._lock = Lock()

	@staticmethod
	def _key(scope: str, identifier: str) -> bytes:
		settings = get_settings()
		value = f"{scope}\0{identifier.strip().casefold()}".encode("utf-8")
		return hmac.digest(settings.SECRET_KEY.encode("utf-8"), value, "sha256")

	def retry_after(
		self,
		scope: str,
		identifier: str,
		limit: int,
		window_seconds: int,
	) -> int:
		key = self._key(scope, identifier)
		now = time.monotonic()
		cutoff = now - window_seconds
		with self._lock:
			attempts = self._attempts.get(key)
			if attempts is None:
				return 0
			while attempts and attempts[0] <= cutoff:
				attempts.popleft()
			if not attempts:
				self._attempts.pop(key, None)
				return 0
			self._attempts.move_to_end(key)
			if len(attempts) < limit:
				return 0
			return max(1, math.ceil(window_seconds - (now - attempts[0])))

	def record(self, scope: str, identifier: str, window_seconds: int) -> None:
		key = self._key(scope, identifier)
		now = time.monotonic()
		cutoff = now - window_seconds
		with self._lock:
			attempts = self._attempts.setdefault(key, deque())
			while attempts and attempts[0] <= cutoff:
				attempts.popleft()
			attempts.append(now)
			self._attempts.move_to_end(key)
			while len(self._attempts) > self.MAX_BUCKETS:
				self._attempts.popitem(last=False)

	def clear(self, scope: str, identifier: str) -> None:
		with self._lock:
			self._attempts.pop(self._key(scope, identifier), None)

	def reset(self) -> None:
		with self._lock:
			self._attempts.clear()


auth_rate_limiter = AuthRateLimiter()
