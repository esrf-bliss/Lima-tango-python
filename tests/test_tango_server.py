"""
Hermetic tests for the LimaCCDs Tango device server: real lima.core +
Simulator camera bindings, no Tango database and no BLISS.

This is a fast, local complement to (not a replacement for) the BLISS
end-to-end baseline (bliss.git: tests/controllers_sw/test_lima_simulator.py,
via lima_simulator_context) - see MIGRATION_ROADMAP.md. That suite is the
only one exercising the real client-facing behavior (scans, controllers);
this one exists to catch server-side regressions fast, in this repo's own
CI, without a BLISS/Redis/Beacon environment.

LimaCCDs.init_device() normally resolves its camera control object by
querying the real Tango database for the sibling camera device's class and
properties (see LimaCCDs._get_control() / EnvHelper.get_lima_camera_type()).
There is no database in a DeviceTestContext, so the `lima_control` fixture
(conftest.py) injects the control object directly through the same
short-circuit _get_control() uses for its own caching (a module-level
`control` global), and stubs get_sub_devices() (queries the DB for sibling
devices; every caller uses dict .get()/.keys(), so an empty dict is a safe
no-op here).
"""
import glob
import os
import time

import pytest
from tango import DevFailed, DevState
from tango.test_context import DeviceTestContext

from lima.server import LimaCCDs


def _wait_ready(proxy, timeout=10):
    deadline = time.time() + timeout
    status = None
    while time.time() < deadline:
        status = proxy.acq_status
        if status == "Ready":
            return
        time.sleep(0.02)
    raise RuntimeError("acquisition did not finish in time, status=%s" % status)


@pytest.fixture(scope="module")
def lima_ccds(lima_control):
    with DeviceTestContext(LimaCCDs.LimaCCDs, process=False, timeout=30) as proxy:
        yield proxy


def test_state_and_identification(lima_ccds):
    assert lima_ccds.state() == DevState.ON
    assert lima_ccds.camera_type == "Simulator"
    assert lima_ccds.lima_version


def test_simple_acquisition(lima_ccds):
    lima_ccds.acq_trigger_mode = "INTERNAL_TRIGGER"
    lima_ccds.acq_expo_time = 0.02
    lima_ccds.acq_nb_frames = 3
    lima_ccds.prepareAcq()
    lima_ccds.startAcq()
    _wait_ready(lima_ccds)
    assert lima_ccds.last_image_acquired == 2


def test_image_geometry(lima_ccds):
    assert lima_ccds.image_width > 0
    assert lima_ccds.image_height > 0

    last_image = lima_ccds.last_image
    assert last_image[0] == "DATA_ARRAY"
    assert len(last_image[1]) > 0


def test_saving_hdf5(lima_ccds, tmp_path):
    lima_ccds.saving_directory = str(tmp_path)
    lima_ccds.saving_prefix = "test_"
    lima_ccds.saving_format = "HDF5"
    lima_ccds.saving_mode = "AUTO_FRAME"
    lima_ccds.acq_nb_frames = 2
    lima_ccds.prepareAcq()
    lima_ccds.startAcq()
    _wait_ready(lima_ccds)

    files = sorted(glob.glob(os.path.join(str(tmp_path), "test_*.h5")))
    assert len(files) == 2


def test_buffer_max_number(lima_ccds):
    lima_ccds.acq_nb_frames = 5
    assert lima_ccds.buffer_max_number >= 5


def test_get_attr_string_value_list(lima_ccds):
    assert "INTERNAL_TRIGGER" in lima_ccds.getAttrStringValueList("acq_trigger_mode")
    assert "EDF" in lima_ccds.getAttrStringValueList("saving_format")


def test_trigger_modes(lima_ccds):
    try:
        for mode in lima_ccds.getAttrStringValueList("acq_trigger_mode"):
            lima_ccds.acq_trigger_mode = mode
            assert lima_ccds.acq_trigger_mode == mode
    finally:
        lima_ccds.acq_trigger_mode = "INTERNAL_TRIGGER"


def test_image_binning_and_roi(lima_ccds):
    width0, height0 = lima_ccds.image_width, lima_ccds.image_height
    try:
        lima_ccds.image_bin = [2, 2]
        assert lima_ccds.image_width == width0 // 2
        assert lima_ccds.image_height == height0 // 2
        lima_ccds.image_bin = [1, 1]

        lima_ccds.image_roi = [10, 10, 100, 50]
        assert lima_ccds.image_width == 100
        assert lima_ccds.image_height == 50
    finally:
        lima_ccds.image_bin = [1, 1]
        lima_ccds.image_roi = [0, 0, 0, 0]
    assert lima_ccds.image_width == width0
    assert lima_ccds.image_height == height0


def test_accumulation_acquisition(lima_ccds):
    try:
        lima_ccds.acc_mode = "THRESHOLD_BEFORE"
        lima_ccds.acc_max_expo_time = 0.01
        lima_ccds.acq_expo_time = 0.05
        lima_ccds.acq_nb_frames = 1
        lima_ccds.prepareAcq()
        lima_ccds.startAcq()
        _wait_ready(lima_ccds)
        assert lima_ccds.last_image_acquired == 0
    finally:
        lima_ccds.acc_mode = "STANDARD"


def test_video_last_image(lima_ccds):
    try:
        lima_ccds.video_active = True
        lima_ccds.acq_trigger_mode = "INTERNAL_TRIGGER"
        lima_ccds.acq_expo_time = 0.02
        lima_ccds.acq_nb_frames = 1
        lima_ccds.prepareAcq()
        lima_ccds.startAcq()
        _wait_ready(lima_ccds)
        video_image = lima_ccds.video_last_image
        assert video_image[0] == "VIDEO_IMAGE"
        assert len(video_image[1]) > 0
    finally:
        lima_ccds.video_active = False


def test_stop_acquisition(lima_ccds):
    lima_ccds.acq_expo_time = 0.5
    lima_ccds.acq_nb_frames = 20
    lima_ccds.prepareAcq()
    lima_ccds.startAcq()
    time.sleep(0.3)
    lima_ccds.stopAcq()
    _wait_ready(lima_ccds)
    assert lima_ccds.acq_status == "Ready"


def test_invalid_trigger_mode_raises(lima_ccds):
    with pytest.raises(DevFailed) as excinfo:
        lima_ccds.acq_trigger_mode = "NOT_A_MODE"
    assert excinfo.value.args[0].reason == "WrongData"


def test_debug_attributes(lima_ccds):
    assert "Warning" in lima_ccds.debug_types_possible
    assert "Common" in lima_ccds.debug_modules_possible

    lima_ccds.debug_types = ["Warning", "Error"]
    assert set(lima_ccds.debug_types) == {"Warning", "Error"}


def test_shutter_manual_commands(lima_ccds):
    # Regression test: closeShutterManual/openShutterManual used to reference
    # core.ShutterManual, which doesn't exist (core.ShutterMode.ShutterManual
    # does) - both always raised AttributeError. Fixed during the Phase 3
    # migration (see MIGRATION_ROADMAP.md).
    assert lima_ccds.shutter_ctrl_is_available
    lima_ccds.closeShutterManual()
    lima_ccds.openShutterManual()


def test_saving_frame_per_file_grouping(lima_ccds, tmp_path):
    lima_ccds.saving_directory = str(tmp_path)
    lima_ccds.saving_prefix = "grp_"
    lima_ccds.saving_format = "EDF"
    lima_ccds.saving_mode = "AUTO_FRAME"
    lima_ccds.saving_frame_per_file = 2
    lima_ccds.acq_nb_frames = 4
    try:
        lima_ccds.prepareAcq()
        lima_ccds.startAcq()
        _wait_ready(lima_ccds)
        files = sorted(glob.glob(os.path.join(str(tmp_path), "grp_*.edf")))
        assert len(files) == 2  # 4 frames / 2 per file
    finally:
        lima_ccds.saving_frame_per_file = 1


def test_saving_next_number_autoincrement(lima_ccds, tmp_path):
    lima_ccds.saving_directory = str(tmp_path)
    lima_ccds.saving_prefix = "inc_"
    lima_ccds.saving_format = "EDF"
    lima_ccds.saving_mode = "AUTO_FRAME"
    lima_ccds.saving_next_number = 5
    lima_ccds.acq_nb_frames = 1
    lima_ccds.prepareAcq()
    lima_ccds.startAcq()
    _wait_ready(lima_ccds)

    assert os.path.exists(os.path.join(str(tmp_path), "inc_0005.edf"))
    assert lima_ccds.saving_next_number == 6


def test_plugin_config_attributes(lima_ccds):
    # No post-processing plugin loaded in this hermetic control - just check
    # the attributes are reachable and correctly typed (empty is expected).
    assert lima_ccds.plugin_type_list == ()
    assert lima_ccds.plugin_list == ()


def test_concat_nb_frames_and_latency_time(lima_ccds):
    try:
        lima_ccds.concat_nb_frames = 2
        assert lima_ccds.concat_nb_frames == 2
        lima_ccds.latency_time = 0.001
        assert lima_ccds.latency_time == pytest.approx(0.001)
    finally:
        lima_ccds.concat_nb_frames = 1
        lima_ccds.latency_time = 0.0


def test_valid_ranges(lima_ccds):
    ranges = lima_ccds.valid_ranges
    assert len(ranges) == 4
    min_expo, max_expo, min_lat, max_lat = ranges
    assert min_expo < max_expo
    assert min_lat < max_lat


def test_read_image_commands(lima_ccds):
    lima_ccds.acq_nb_frames = 2
    lima_ccds.prepareAcq()
    lima_ccds.startAcq()
    _wait_ready(lima_ccds)

    last_image = lima_ccds.readLastImage(-1)
    assert last_image[0] == "DATA_ARRAY"
    assert len(last_image[1]) > 0

    first_image = lima_ccds.readImage(0)
    assert first_image[0] == "DATA_ARRAY"
    assert len(first_image[1]) > 0


def test_set_image_header(lima_ccds):
    lima_ccds.setImageHeader(["0;key1=value1"])
    lima_ccds.resetCommonHeader()
    lima_ccds.resetFrameHeaders()


def test_abort_acquisition(lima_ccds):
    lima_ccds.acq_expo_time = 0.3
    lima_ccds.acq_nb_frames = 10
    lima_ccds.prepareAcq()
    lima_ccds.startAcq()
    time.sleep(0.2)
    lima_ccds.abortAcq()
    _wait_ready(lima_ccds)
    assert lima_ccds.acq_status == "Ready"
