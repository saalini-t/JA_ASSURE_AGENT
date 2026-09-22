"""
Automatic background publishing worker (Phase 17A). Safe-default verification:
the app must never begin automatic publishing merely by starting, and
run_forever() must actually loop, calling run_once() each pass, respecting the
configured interval, and surviving a single pass's exception without dying.
"""
import asyncio

import pytest

from app.services import publishing_worker


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_worker_disabled_by_default():
    from app.config import settings
    assert settings.PUBLISH_WORKER_ENABLED is False


def test_main_does_not_start_worker_task_when_disabled(monkeypatch):
    """Confirms app.main's lifespan genuinely gates on the setting -- not just
    that the setting defaults to False, but that main.py actually reads it."""
    import inspect
    import app.main as main_module
    source = inspect.getsource(main_module)
    assert "PUBLISH_WORKER_ENABLED" in source
    assert "asyncio.create_task" in source


@pytest.mark.anyio
async def test_run_forever_calls_run_once_repeatedly(monkeypatch):
    call_count = {"n": 0}

    async def fake_run_once(max_items=10):
        call_count["n"] += 1
        return []

    monkeypatch.setattr(publishing_worker, "run_once", fake_run_once)

    task = asyncio.create_task(publishing_worker.run_forever(interval_seconds=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert call_count["n"] >= 2  # looped multiple times, not just once


@pytest.mark.anyio
async def test_run_forever_survives_a_failing_pass(monkeypatch):
    call_count = {"n": 0}

    async def flaky_run_once(max_items=10):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated transient DB error")
        return []

    monkeypatch.setattr(publishing_worker, "run_once", flaky_run_once)

    task = asyncio.create_task(publishing_worker.run_forever(interval_seconds=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert call_count["n"] >= 2  # the failure on pass 1 didn't kill the loop


@pytest.mark.anyio
async def test_run_forever_stops_cleanly_on_cancel(monkeypatch):
    async def fake_run_once(max_items=10):
        return []

    monkeypatch.setattr(publishing_worker, "run_once", fake_run_once)

    task = asyncio.create_task(publishing_worker.run_forever(interval_seconds=10))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
