import asyncio
from app.error_handlers import handle_api_errors, handle_data_errors, error_registry, ErrorSeverity, error_handler

@handle_api_errors
async def failing_api():
    raise RuntimeError("api boom")

@handle_data_errors
def failing_data():
    raise ValueError("data boom")

async def _run():
    # Clear existing errors
    error_registry.errors.clear()
    error_registry.error_counts.clear()
    await failing_api()
    failing_data()
    stats = error_registry.get_error_stats()
    assert stats['total_errors'] == 2
    assert 'RuntimeError' in stats['by_type'] and 'ValueError' in stats['by_type']


def test_error_handler_decorators():
    asyncio.run(_run())
