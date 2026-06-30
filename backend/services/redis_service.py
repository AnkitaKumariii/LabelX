import redis.asyncio as aioredis
import json
import os
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None

class MockRedis:
    def __init__(self):
        self.file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.redis_mock.json')
        self.data = {}
        self.lists = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    self.data = content.get('data', {})
                    self.lists = content.get('lists', {})
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({'data': self.data, 'lists': self.lists}, f)
        except Exception:
            pass

    async def set(self, key, value, ex=None):
        self._load()
        self.data[key] = value
        self._save()

    async def get(self, key):
        self._load()
        return self.data.get(key)

    async def delete(self, key):
        self._load()
        if key in self.data:
            del self.data[key]
            self._save()

    async def lpush(self, key, *values):
        self._load()
        if key not in self.lists:
            self.lists[key] = []
        for v in values:
            self.lists[key].insert(0, v)
        self._save()

    async def ltrim(self, key, start, end):
        self._load()
        if key in self.lists:
            self.lists[key] = self.lists[key][start:end+1]
            self._save()

    async def lrange(self, key, start, end):
        self._load()
        if key in self.lists:
            if end == -1:
                return self.lists[key][start:]
            return self.lists[key][start:end+1]
        return []

    async def expire(self, key, time):
        pass

    async def ping(self):
        return True

_mock_instance = MockRedis()
_use_mock = False


async def get_redis():
    global _redis_client, _use_mock
    if _use_mock:
        return _mock_instance

    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            temp_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=1,
            )
            await temp_client.ping()
            _redis_client = temp_client
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory MockRedis.")
            _use_mock = True
            return _mock_instance

    return _redis_client


# ── Profile helpers ────────────────────────────────────────────────────────────

async def save_profile(profile_id: str, profile: Dict[str, Any]) -> None:
    r = await get_redis()
    await r.set(f"profile:{profile_id}", json.dumps(profile), ex=60 * 60 * 24 * 30)  # 30 days


async def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    r = await get_redis()
    raw = await r.get(f"profile:{profile_id}")
    if raw:
        return json.loads(raw)
    return None


async def delete_profile(profile_id: str) -> None:
    r = await get_redis()
    await r.delete(f"profile:{profile_id}")


# ── Analysis history helpers ───────────────────────────────────────────────────

async def save_analysis(profile_id: str, analysis: Dict[str, Any]) -> None:
    r = await get_redis()
    key = f"history:{profile_id}"
    await r.lpush(key, json.dumps(analysis))
    await r.ltrim(key, 0, 49)          # Keep last 50 analyses
    await r.expire(key, 60 * 60 * 24 * 90)  # 90 days


async def get_history(profile_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    r = await get_redis()
    raw_list = await r.lrange(f"history:{profile_id}", 0, limit - 1)
    return [json.loads(item) for item in raw_list]


# ── Tavily Cache helpers ───────────────────────────────────────────────────────

async def get_tavily_cache(ingredient: str) -> Optional[Dict[str, Any]]:
    r = await get_redis()
    raw = await r.get(f"tavily:{ingredient.lower()}")
    if raw:
        return json.loads(raw)
    return None

async def set_tavily_cache(ingredient: str, data: Dict[str, Any]) -> None:
    r = await get_redis()
    await r.set(f"tavily:{ingredient.lower()}", json.dumps(data), ex=60 * 60 * 24)  # 24 hours


# ── Health check ──────────────────────────────────────────────────────────────

async def ping_redis() -> bool:
    try:
        r = await get_redis()
        return await r.ping()
    except Exception as e:
        logger.error(f"Redis ping failed: {e}")
        return False
