"""
Hermetic tests for the generic post-processing plugin devices (Mask,
RoiCounter, BackgroundSubstraction, FlatField, RoiCollection, Roi2Spectrum):
real lima.core + Simulator camera bindings, no Tango database and no BLISS.
See test_tango_server.py for the rationale/harness notes shared with this
file, and MIGRATION_ROADMAP.md for the plugin migration status (only
Mask.py is on the high-level API so far; the others are tested here
unmigrated, to prove old-style/high-level coexistence - see the mapping
guide).

Each plugin device shares the running control object with LimaCCDs through
the same `_control_ref` weakref mechanism used in production (LimaCCDs's
`_set_control_ref()` calls `<plugin_module>.set_control_ref()` for every
loaded plugin) - wired up here from the shared `lima_control` fixture
(conftest.py), for the same reason `LimaCCDs.control` is injected there.
`Simulator.get_control()` registers native callbacks on the camera
interface that cannot be registered twice in the same process, so it must
be built exactly once per test session - shared with test_tango_server.py
through that fixture rather than called again here.

A `tango.server.Device` (Mask, and LimaCCDs itself) can't be registered in
the same `MultiDeviceTestContext` as a classical low-level PyTango.DeviceClass
device (pytango raises "mixing HLAPI and classical API in devices_info is
not supported") - every device below is therefore registered through its
`[DeviceClass, DeviceImpl]` pair (the same classical form `util.add_class()`
accepts in production), including the already-migrated Mask and LimaCCDs via
their auto-generated `.TangoClassClass`.

All plugins here are started together in a *single* shared context (one
`MultiDeviceTestContext`, module-scoped fixture) rather than one context per
test: opening several separate `MultiDeviceTestContext(process=False, ...)`
in sequence within the same process was observed to segfault (the native
Tango/CORBA layer doesn't tear down cleanly between them - the same root
cause noted for DeviceTestContext in the Basler/Maxipix smoke tests). A
single shared context with several plugins active simultaneously is fine
and mirrors real deployments (a `LimaCCDs` server commonly runs several
post-processing plugins at once) - it does require each plugin to be given
a distinct `RunLevel` first (`BasePostProcess.RunLevel`, writable only while
the device is OFF): the native `SoftOpExternalMgr` raises "task already
active on that level" if two operators default to the same level (0).
`BackgroundSubstraction` occupies its own level *and* level+1 internally
(background-image-update task, then the substraction task) - leave a gap.

PeakFinder.py is excluded: `Start()` + a plain acquisition + `readPeaks()`
against the Simulator's default frame segfaults even in complete isolation,
with no plugin combination involved - a pre-existing native crash unrelated
to any migration work (the file is untouched), not chased further here.
LimaTacoCCD.py is excluded on purpose (legacy SPEC compatibility shim, kept
for 2 beamlines, not part of the tango.server migration effort). Memcached.py
(needs a real memcached server) and LiveViewer.py (needs a live viewer/
display) are excluded as impractical to run hermetically.
"""
import time
import weakref

import fabio
import numpy
import pytest
from tango import DevState
from tango.test_context import MultiDeviceTestContext

from lima.server import LimaCCDs
from lima.server.plugins import (
    BackgroundSubstraction,
    FlatField,
    Mask,
    Roi2Spectrum,
    RoiCollection,
    RoiCounter,
)


def _wait_ready(proxy, timeout=10):
    deadline = time.time() + timeout
    status = None
    while time.time() < deadline:
        status = proxy.acq_status
        if status == "Ready":
            return
        time.sleep(0.02)
    raise RuntimeError("acquisition did not finish in time, status=%s" % status)


def _edf(tmp_path_factory, data):
    path = str(tmp_path_factory.mktemp("data") / "img.edf")
    fabio.edfimage.EdfImage(data).save(path)
    return path


@pytest.fixture(scope="module")
def plugins(lima_control, tmp_path_factory):
    ref = weakref.ref(lima_control)
    for mod in (Mask, RoiCounter, BackgroundSubstraction, FlatField, RoiCollection, Roi2Spectrum):
        mod.set_control_ref(ref)

    mask_data = numpy.zeros((1024, 1024), dtype=numpy.uint8)
    mask_data[0:10, 0:10] = 1
    mask_file = _edf(tmp_path_factory, mask_data)

    flat = numpy.ones((1024, 1024), dtype=numpy.uint32)
    flat_file = _edf(tmp_path_factory, flat)

    devices_info = (
        {
            "class": [LimaCCDs.LimaCCDs.TangoClassClass, LimaCCDs.LimaCCDs],
            "devices": [{"name": "test/limaccds/1"}],
        },
        {
            "class": [Mask.MaskDeviceServer.TangoClassClass, Mask.MaskDeviceServer],
            "devices": [{"name": "test/mask/1"}],
        },
        {
            "class": [
                RoiCounter.RoiCounterDeviceServerClass,
                RoiCounter.RoiCounterDeviceServer,
            ],
            "devices": [{"name": "test/roicounter/1", "properties": {"BufferSize": "128"}}],
        },
        {
            "class": [
                BackgroundSubstraction.BackgroundSubstractionDeviceServerClass,
                BackgroundSubstraction.BackgroundSubstractionDeviceServer,
            ],
            "devices": [{"name": "test/background/1"}],
        },
        {
            "class": [FlatField.FlatfieldDeviceServerClass, FlatField.FlatfieldDeviceServer],
            "devices": [{"name": "test/flatfield/1"}],
        },
        {
            "class": [
                RoiCollection.RoiCollectionDeviceServerClass,
                RoiCollection.RoiCollectionDeviceServer,
            ],
            "devices": [{"name": "test/roicollection/1"}],
        },
        {
            "class": [
                Roi2Spectrum.Roi2spectrumDeviceServerClass,
                Roi2Spectrum.Roi2spectrumDeviceServer,
            ],
            "devices": [{"name": "test/roi2spectrum/1"}],
        },
    )

    with MultiDeviceTestContext(devices_info, process=False, timeout=30) as ctx:
        lima = ctx.get_device("test/limaccds/1")
        mask = ctx.get_device("test/mask/1")
        roi = ctx.get_device("test/roicounter/1")
        bg = ctx.get_device("test/background/1")
        ff = ctx.get_device("test/flatfield/1")
        rc = ctx.get_device("test/roicollection/1")
        r2s = ctx.get_device("test/roi2spectrum/1")

        mask.RunLevel = 0
        mask.setMaskFile(mask_file)
        mask.Start()

        roi.RunLevel = 1
        roi.Start()
        (roi_id,) = roi.addNames(["r1"])
        roi.setRois([roi_id, 10, 10, 50, 50])

        bg.RunLevel = 2  # occupies levels 2 and 3 internally
        bg.setBackgroundFile(flat_file)
        bg.Start()

        ff.RunLevel = 4
        ff.setFlatFieldFile(flat_file)
        ff.Start()

        rc.RunLevel = 5
        rc.Start()
        rc.setRois([10, 10, 20, 20, 40, 40, 20, 20])  # 2 rois, 20x20 each

        r2s.RunLevel = 6
        r2s.Start()
        (roi2s_id,) = r2s.addNames(["s1"])
        r2s.setRois([roi2s_id, 10, 10, 50, 50])

        yield {
            "lima": lima,
            "mask": mask,
            "roi": (roi, roi_id),
            "background": bg,
            "flatfield": ff,
            "roicollection": rc,
            "roi2spectrum": (r2s, roi2s_id),
        }


def test_all_plugins_active(plugins):
    for key in ("mask", "background", "flatfield", "roicollection"):
        assert plugins[key].state() == DevState.ON
    assert plugins["roi"][0].state() == DevState.ON
    assert plugins["roi2spectrum"][0].state() == DevState.ON


def test_acquisition_with_all_plugins_active(plugins):
    lima = plugins["lima"]
    lima.acq_nb_frames = 3
    lima.prepareAcq()
    lima.startAcq()
    _wait_ready(lima)
    assert lima.last_image_acquired == 2


def test_mask(plugins):
    assert plugins["mask"].type == "STANDARD"


def test_roi_counter(plugins):
    roi, roi_id = plugins["roi"]
    assert list(roi.getNames()) == ["r1"]
    assert list(roi.getRois(["r1"])) == [roi_id, 10, 10, 50, 50]

    counters = roi.readCounters(0)
    assert len(counters) % 7 == 0  # (roi_id, frame_nb, sum, avg, std, min, max) rows
    assert len(counters) > 0


def test_roi_collection(plugins):
    rc = plugins["roicollection"]
    spectrum = rc.readSpectrum(0)
    nb_frames, spectrum_size = spectrum[0], spectrum[1]
    assert nb_frames > 0
    assert spectrum_size == 2  # 2 rois in the collection


def test_roi2spectrum(plugins):
    r2s, roi_id = plugins["roi2spectrum"]
    assert list(r2s.getNames()) == ["s1"]
    spectrum = r2s.readImage([roi_id, -1])
    assert len(spectrum) % 50 == 0  # roi width, one spectrum row per frame in history
    assert len(spectrum) > 0
