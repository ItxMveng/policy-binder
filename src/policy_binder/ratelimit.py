"""Protection de la démo publique : limite par adresse IP et quota quotidien global.

Compteurs en mémoire : exacts avec une seule instance (le déploiement de démo est limité à une
instance) ; avec plusieurs instances, il faudrait un stockage partagé (Redis, Firestore).
"""

import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime

MAX_TRACKED_IPS = 10_000


def client_ip(forwarded_for: str | None, peer: str | None) -> str:
    """Adresse du client. Derrière le proxy de Cloud Run, c'est la dernière valeur de
    X-Forwarded-For, ajoutée par le proxy lui-même ; les valeurs précédentes peuvent être
    écrites par le client et ne sont donc pas fiables."""
    if forwarded_for:
        last = forwarded_for.split(",")[-1].strip()
        if last:
            return last
    return peer or "inconnu"


class DemoLimiter:
    def __init__(
        self,
        per_ip: int,
        window_s: float,
        daily: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.per_ip = per_ip
        self.window_s = window_s
        self.daily = daily
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._day = ""
        self._day_count = 0

    def check(self, ip: str) -> str | None:
        """Enregistre la demande si elle est autorisée ; sinon renvoie la raison du refus."""
        now = self._clock()
        day = datetime.fromtimestamp(now, UTC).date().isoformat()
        if day != self._day:  # nouveau jour (UTC) : le quota global repart de zéro
            self._day, self._day_count = day, 0
        if self._day_count >= self.daily:
            return "Quota quotidien de la démo atteint, réessayez demain."

        hits = self._hits.setdefault(ip, deque())
        while hits and hits[0] <= now - self.window_s:
            hits.popleft()
        if len(hits) >= self.per_ip:
            wait_min = max(1, round((hits[0] + self.window_s - now) / 60))
            return f"Trop de questions depuis votre adresse, réessayez dans {wait_min} min."

        hits.append(now)
        self._day_count += 1
        if len(self._hits) > MAX_TRACKED_IPS:
            self._forget_idle(now)
        return None

    def _forget_idle(self, now: float) -> None:
        idle = [
            ip for ip, hits in self._hits.items() if not hits or hits[-1] <= now - self.window_s
        ]
        for ip in idle:
            del self._hits[ip]
