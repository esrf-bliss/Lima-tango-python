"""
Shared fixtures for the hermetic (no Tango DB, no BLISS) Tango server tests.
See test_tango_server.py for the full rationale.
"""
import pytest

from lima.server import LimaCCDs
from lima.server.camera import Simulator


@pytest.fixture(scope="session")
def lima_control():
    """Build the real Simulator camera/interface/control exactly once for the
    whole test session, and inject it as LimaCCDs's module-level `control`
    global (the short-circuit LimaCCDs._get_control() caches on).

    core.CtControl(interface) registers callbacks on the interface that
    cannot be registered twice - calling Simulator.get_control() more than
    once per process fails ("ValidRangesCallback already registered"), so
    this must stay session-scoped and shared by every test module that
    needs a running control (test_tango_server.py, test_tango_plugins.py).
    """
    control = Simulator.get_control()
    LimaCCDs.control = control
    # init_device() also calls get_sub_devices() (queries the real Tango DB
    # for sibling devices of the running server instance) - not available/
    # meaningful in a hermetic, db-less test context. Short-circuit it;
    # every caller uses .get()/.keys(), safe with an empty dict.
    LimaCCDs.get_sub_devices = lambda *a, **kw: {}
    return control
