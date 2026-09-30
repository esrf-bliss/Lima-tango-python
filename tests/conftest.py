"""
Shared fixtures for the hermetic (no Tango DB, no BLISS) Tango server tests.
See test_tango_server.py for the full rationale.
"""
import pytest

from lima.server import LimaCCDs
from lima.server.camera import Simulator


@pytest.fixture(scope="session")
def lima_control():
    """Build the real control once per session and inject it as LimaCCDs's
    `control` global (the short-circuit LimaCCDs._get_control() caches on).
    core.CtControl(interface) can't register its callbacks twice, so this
    must be session-scoped and shared by every module that needs a control.
    """
    control = Simulator.get_control()
    LimaCCDs.control = control
    # get_sub_devices() queries the real Tango DB for sibling devices - not
    # available here; every caller uses .get()/.keys(), so {} is a safe stub.
    LimaCCDs.get_sub_devices = lambda *a, **kw: {}
    return control
