"""
Hermetic tests for the generic post-processing plugins (Mask, RoiCounter,
BackgroundSubstraction, FlatField, RoiCollection, Roi2Spectrum): real
lima.core + Simulator bindings, no Tango database and no BLISS. Only
Mask.py is migrated so far; the rest are tested unmigrated, to prove
old-style/high-level coexistence.

Each plugin gets the shared control via `set_control_ref()` (the same
`_control_ref` weakref mechanism LimaCCDs uses in production), from the
`lima_control` fixture in conftest.py.

`MultiDeviceTestContext` can't mix a `tango.server.Device` (Mask, LimaCCDs)
with a classical low-level one in the same call, so every device here is
registered via its `[DeviceClass, DeviceImpl]` pair (the same form
`util.add_class()` accepts).

All plugins are started together in one shared context rather than one per
test: separate sequential `MultiDeviceTestContext`s segfault the native
CORBA/ORB layer within one process. Running several at once mirrors real
deployments, but needs a distinct `RunLevel` per plugin (writable only
while OFF) - the native `SoftOpExternalMgr` rejects two operators on the
same level. `BackgroundSubstraction` occupies its level *and* level+1.

Excluded: `PeakFinder.py` (segfaults on Start()+acquire+readPeaks() even
alone - pre-existing, unrelated to migration), `LimaTacoCCD.py` (legacy
SPEC shim, kept for 2 beamlines), `Memcached.py`/`LiveViewer.py` (need a
real memcached server / display).
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
