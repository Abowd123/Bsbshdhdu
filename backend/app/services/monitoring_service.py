"""
خدمة مراقبة موارد الحاويات (CPU / RAM / عدد العمليات).

- تقرأ القراءات مباشرة من Docker Stats API (نفس الـ API المستخدم في
  docker_engine.py لكن بعميل Docker منفصل خاص بهذه الخدمة فقط، دون أي
  تعديل على docker_engine.py).
- تخزّن آخر قراءة لكل بوت في Redis (مفتاح خاص لكل bot_id) بدل قاعدة
  البيانات لتقليل الحمل على الـ DB، مع انتهاء صلاحية (TTL) تلقائي حتى
  تختفي القراءة لو توقّفت الحاوية عن العمل.
"""

import asyncio
import json
import time

import docker
from docker.errors import NotFound
import redis.asyncio as aioredis

from app.core.config import settings

REDIS_STATS_PREFIX = "bot:stats:"
REDIS_STATS_TTL_SECONDS = 30  # أكبر قليلاً من فترة الجمع (10 ثواني) لتفادي القراءات القديمة
POLL_INTERVAL_SECONDS = 10


class MonitoringServiceError(Exception):
    pass


class MonitoringService:
    def __init__(self) -> None:
        # عميل Docker مستقل خاص بخدمة المراقبة فقط (لا نلمس docker_engine.py)
        self._docker_client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _redis_key(self, bot_id: str) -> str:
        return f"{REDIS_STATS_PREFIX}{bot_id}"

    def _read_container_stats(self, container_name: str) -> dict | None:
        """قراءة لقطة واحدة (بدون stream) من Docker Stats API لحاوية معيّنة."""
        try:
            container = self._docker_client.containers.get(container_name)
            if container.status != "running":
                return None
            raw = container.stats(stream=False)
        except NotFound:
            return None
        except Exception:
            return None
        return self._parse(raw)

    def _parse(self, raw: dict) -> dict:
        cpu_stats = raw.get("cpu_stats", {})
        precpu_stats = raw.get("precpu_stats", {})
        cpu_usage = cpu_stats.get("cpu_usage", {})
        precpu_usage = precpu_stats.get("cpu_usage", {})

        cpu_delta = cpu_usage.get("total_usage", 0) - precpu_usage.get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
        cpu_count = cpu_stats.get("online_cpus") or len(cpu_usage.get("percpu_usage") or [1]) or 1

        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

        mem_stats = raw.get("memory_stats", {})
        mem_usage = mem_stats.get("usage", 0)
        mem_limit = mem_stats.get("limit", 1) or 1

        pids_stats = raw.get("pids_stats", {})
        process_count = pids_stats.get("current", 0)

        networks = raw.get("networks", {}) or {}

        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage_mb": round(mem_usage / 1024 / 1024, 2),
            "memory_limit_mb": round(mem_limit / 1024 / 1024, 2),
            "memory_percent": round((mem_usage / mem_limit) * 100, 2) if mem_limit else 0.0,
            "process_count": process_count,
            "network_rx_bytes": sum(v.get("rx_bytes", 0) for v in networks.values()),
            "network_tx_bytes": sum(v.get("tx_bytes", 0) for v in networks.values()),
            "collected_at": time.time(),
        }

    async def collect_and_store(self, bot_id: str, container_name: str) -> dict | None:
        """يقرأ القراءة الحالية للحاوية ويخزّنها في Redis. يُستخدم من مهمة Celery Beat
        وأيضًا كـ fallback في الـ endpoint عند عدم وجود قراءة مخزّنة بعد."""
        loop = asyncio.get_running_loop()
        stats = await loop.run_in_executor(None, self._read_container_stats, container_name)
        if stats is None:
            return None
        redis_client = await self._get_redis()
        await redis_client.set(self._redis_key(bot_id), json.dumps(stats), ex=REDIS_STATS_TTL_SECONDS)
        return stats

    async def get_latest(self, bot_id: str) -> dict | None:
        """يرجع آخر قراءة مخزّنة في Redis لهذا البوت، أو None إن لم توجد."""
        redis_client = await self._get_redis()
        raw = await redis_client.get(self._redis_key(bot_id))
        if raw is None:
            return None
        return json.loads(raw)


monitoring_service = MonitoringService()
