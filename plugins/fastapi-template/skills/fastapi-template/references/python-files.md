# Python File Templates

Replace `<app-name>` with the actual app name throughout.

---

## `app/__init__.py`

```python
import os

from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("DOT_ENV_PATH", ".env"))
templates = Jinja2Templates(directory="templates")


def _assert_env(name: str) -> None:
    if not os.getenv(name):
        raise RuntimeError(f"Configuration missing: {name}")


_assert_env("ENGINE_URL")
_assert_env("REDIS_CONNECTION_STRING")
_assert_env("SESSION_SECRET")
# Add additional required vars here
```

---

## `app/main.py`

```python
import os
import sys
import time

from loguru import logger
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler as _default_http_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from .routers.home import home_router
from .dependencies import DB_ENGINE

DEV_MODE = os.getenv("DEV_MODE", "OFF") == "ON"
REDIS_URL = os.getenv("REDIS_CONNECTION_STRING")

logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG" if DEV_MODE else "INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} | {message}",
    colorize=DEV_MODE,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(f"Starting <app-name> (DEV_MODE={DEV_MODE})")
    redis = aioredis.from_url(REDIS_URL)
    try:
        await redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    app.state.redis = redis
    cache_prefix = "<app-name>"
    if DEV_MODE:
        cache_prefix += "-dev"
    FastAPICache.init(RedisBackend(redis), prefix=cache_prefix)
    yield
    await redis.close()
    logger.info("Redis connection closed")
    try:
        DB_ENGINE.dispose()
        logger.info("DB connection pool disposed")
    except Exception as e:
        logger.warning(f"DB pool dispose error during shutdown: {e}")


app = FastAPI(title="<app-name>", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(home_router)
# Add more routers here


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)"
    )
    if DEV_MODE and request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/", status_code=303)
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}"
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}"
        )
    return await _default_http_handler(request, exc)
```

**If no AI/Redis**: remove `FastAPICache`, `RedisBackend`, `aioredis` imports; remove lifespan Redis block; remove `cache_prefix`; simplify `lifespan` to just `yield`.

---

## `app/dependencies.py`

```python
import asyncio
import os
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, create_engine

from .utils import get_cookie

ENGINE_URL = os.getenv("ENGINE_URL")
# pool_size and max_overflow are per-worker (each gunicorn worker is a separate process).
# Both are scaled so that workers × (pool_size + max_overflow) stays at ~24 regardless of
# worker count (e.g. 4 workers → 5+1=6 each → 24 total; 8 workers → 2+0=2 each → 16 total).
_WEB_CONCURRENCY = max(1, int(os.getenv("WEB_CONCURRENCY", "4") or "4"))
_POOL_PER_WORKER = max(1, 20 // _WEB_CONCURRENCY)
DB_ENGINE = create_engine(
    ENGINE_URL,
    pool_size=_POOL_PER_WORKER,
    max_overflow=max(0, 4 // _WEB_CONCURRENCY),
    pool_recycle=300,
    pool_pre_ping=True,
)

# Retry config for serverless containers that may be sleeping on first request.
_DB_PING_RETRIES = int(os.getenv("DB_PING_RETRIES", "5"))
_DB_PING_INTERVAL = float(os.getenv("DB_PING_INTERVAL", "2"))
_REDIS_PING_RETRIES = int(os.getenv("REDIS_PING_RETRIES", "5"))
_REDIS_PING_INTERVAL = float(os.getenv("REDIS_PING_INTERVAL", "2"))


def get_db_session():
    for attempt in range(_DB_PING_RETRIES):
        try:
            with DB_ENGINE.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except OperationalError:
            if attempt == _DB_PING_RETRIES - 1:
                raise
            logger.warning(
                f"DB ping failed (attempt {attempt + 1}/{_DB_PING_RETRIES}), retrying in {_DB_PING_INTERVAL}s"
            )
            time.sleep(_DB_PING_INTERVAL)

    with Session(DB_ENGINE) as session:
        yield session


DBSessionDependency = Annotated[Session, Depends(get_db_session)]


async def get_redis(request: Request):
    redis = request.app.state.redis
    for attempt in range(_REDIS_PING_RETRIES):
        try:
            await redis.ping()
            return redis
        except Exception:
            if attempt == _REDIS_PING_RETRIES - 1:
                raise
            logger.warning(
                f"Redis ping failed (attempt {attempt + 1}/{_REDIS_PING_RETRIES}), retrying in {_REDIS_PING_INTERVAL}s"
            )
            await asyncio.sleep(_REDIS_PING_INTERVAL)


RedisDependency = Annotated[object, Depends(get_redis)]


def require_auth(request: Request):
    if not get_cookie(request, "user_id"):
        raise HTTPException(status_code=401)


RequireAuthDependency = Annotated[None, Depends(require_auth)]


def is_authenticated(request: Request) -> bool:
    return bool(get_cookie(request, "user_id"))


IsAuthenticatedDependency = Annotated[bool, Depends(is_authenticated)]
```

The ping retries (the `_DB_PING_*` / `_REDIS_PING_*` settings and the retry loops in `get_db_session` and `get_redis`) are only when host is `railway`. With `--host generic`, drop them and the imports only they use (`asyncio`, `time`, `logger`, `text`, `OperationalError`): `get_db_session` is just `with Session(DB_ENGINE) as session: yield session`, and `get_redis` is just `return request.app.state.redis`.

---

## `app/ai.py`

```python
import os
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger
from openrouter import OpenRouter
from fastapi_cache.decorator import cache

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("Configuration missing: OPENROUTER_API_KEY")

_prompt_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR / "prompts"))


def render_prompt(name: str, **context) -> str:
    return _prompt_env.get_template(f"{name}.txt").render(**context).strip()


@cache(namespace="ai-model")
async def invoke_ai_model(
    *messages,
    system_prompt_name=None,
    prompt_context=None,
    model="openai/gpt-4o-mini",
    temperature=0,
    **extra_model_kwargs,
):
    if system_prompt_name is not None:
        system_prompt = render_prompt(system_prompt_name, **(prompt_context or {}))
        logger.debug(f"System prompt:\n{system_prompt}")
        messages = [dict(role="system", content=system_prompt)] + list(messages)

    logger.debug(f"Calling AI model {model!r}")
    with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
        response = client.chat.send(
            messages=list(messages),
            model=model,
            temperature=temperature,
            **extra_model_kwargs,
        )
        logger.debug(f"Response usage: {response.usage}")

    return response


async def get_ai_response(*messages, **kwargs) -> str:
    response = await invoke_ai_model(*messages, **kwargs)
    if isinstance(response, dict):
        # Deserialized from Redis cache
        content = response["choices"][0]["message"]["content"].strip()
    else:
        content = response.choices[0].message.content.strip()
    logger.debug(f"AI response: {content[:300]}")
    return content


async def get_ai_json_response(*messages, **kwargs) -> dict:
    content = await get_ai_response(*messages, top_p=1, **kwargs)
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        content = content[start : end + 1]
    return json.loads(content)
```

Write the `--ai-model` value as the `model` default in `invoke_ai_model` (`openai/gpt-4o-mini` when the flag is not given).

---

## `app/db/__init__.py`

```python
```

## `app/db/models.py`

```python
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


# Replace with your actual domain models.
# Always set __tablename__ explicitly.
# Always use UUID primary keys with default_factory=uuid4.

class Item(SQLModel, table=True):
    __tablename__ = "items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: Optional[str] = None
```

## `app/db/crud.py`

```python
from pydantic import BaseModel
from sqlmodel import Session, SQLModel


def update_db_element(db: Session, original: SQLModel, update: BaseModel) -> SQLModel:
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(original, key, value)
    db.add(original)
    db.commit()
    db.refresh(original)
    return original


def delete_db_element(db: Session, element: SQLModel) -> None:
    db.delete(element)
    db.commit()
```

---

## `app/routers/__init__.py`

```python
```

## `app/routers/home.py`

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .. import templates

home_router = APIRouter()


@home_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
```

---

## `app/schemas/__init__.py`

```python
```

---

## `app/utils.py`

```python
import hmac
import hashlib
import os

from fastapi import Request
from fastapi.responses import Response

SESSION_SECRET = os.getenv("SESSION_SECRET", "")
DEV_MODE = os.getenv("DEV_MODE", "").upper() == "ON"


def _sign(value: str) -> str:
    sig = hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"


def _verify(signed: str) -> str | None:
    if "." not in signed:
        return None
    value, sig = signed.rsplit(".", 1)
    expected = hmac.new(
        SESSION_SECRET.encode(), value.encode(), hashlib.sha256
    ).hexdigest()
    if hmac.compare_digest(sig, expected):
        return value
    return None


def get_cookie(request: Request, name: str) -> str | None:
    return _verify(request.cookies.get(name, ""))


def set_cookie(
    response: Response,
    name: str,
    value: str,
    *,
    httponly: bool = True,
    secure: bool = not DEV_MODE,
    samesite: str = "lax",
    max_age: int = 86400 * 30,
) -> None:
    response.set_cookie(
        name,
        _sign(value),
        httponly=httponly,
        secure=secure,
        samesite=samesite,
        max_age=max_age,
    )
```
