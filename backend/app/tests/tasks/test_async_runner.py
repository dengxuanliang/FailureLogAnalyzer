import asyncio

from app.tasks import async_runner


def teardown_function() -> None:
    loop = async_runner._worker_loop
    if loop is not None and not loop.is_closed():
        loop.close()
    async_runner._worker_loop = None


async def _loop_id() -> int:
    return id(asyncio.get_running_loop())


def test_run_async_in_worker_reuses_same_loop():
    first = async_runner.run_async_in_worker(_loop_id())
    second = async_runner.run_async_in_worker(_loop_id())

    assert first == second


def test_run_async_in_worker_recreates_closed_loop():
    first = async_runner.run_async_in_worker(_loop_id())
    async_runner._worker_loop.close()

    second = async_runner.run_async_in_worker(_loop_id())

    assert first != second
