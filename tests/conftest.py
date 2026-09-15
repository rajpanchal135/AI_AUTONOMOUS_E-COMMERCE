import asyncio
import inspect
import pytest

def pytest_pyfunc_call(pyfuncitem):
    """Allow running async test functions without external pytest-asyncio plugin."""
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        argnames = pyfuncitem._fixtureinfo.argnames
        args = [pyfuncitem.funcargs[arg] for arg in argnames]
        asyncio.run(testfunction(*args))
        return True
