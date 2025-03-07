############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2022
# European Synchrotron Radiation Facility
# CS40220 38043 Grenoble Cedex 9
# FRANCE
# Contact: lima@esrf.fr
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
############################################################################
import PyTango
import numpy
import time
import struct
import threading
import weakref

from Lima import Core
from Lima.Server.plugins.Utils import BasePostProcess


# PIL an StringIO, py2 vs. py3
try:
    import Image
except ImportError:
    from PIL import Image

try:
    from cString import StringIO
except ImportError:
    from io import BytesIO as StringIO

# 3-4x faster jpeg encoding than PIL
# https://github.com/lilohuang/PyTurboJPEG
try:
    from turbojpeg import TurboJPEG, TJPF_RGB

    turbo_jpeg = TurboJPEG()
except ImportError:
    turbo_jpeg = None

import base64


# ==================================================================
#   Bpm Class Description:
#
#
# ==================================================================


class BpmDeviceServer(BasePostProcess):
    Core.DEB_CLASS(Core.DebModApplication, "BpmDeviceServer")

    # --------- Add you global variables here --------------------------
    BPM_TASK_NAME = "BpmTask"
    BVDATA_TASK_NAME = "BVDataTask"

    ImageType2Bpp = {
        Core.Bpp8: 8,
        Core.Bpp10: 10,
        Core.Bpp12: 12,
        Core.Bpp14: 14,
        Core.Bpp16: 16,
        Core.Bpp32: 32,
        Core.Bpp8S: 7,
        Core.Bpp10S: 9,
        Core.Bpp12S: 11,
        Core.Bpp14S: 13,
        Core.Bpp16S: 15,
        Core.Bpp32S: 31,
    }
    # ------------------------------------------------------------------
    #    Device constructor
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def __init__(self, cl, name):
        self._softOp = None
        self._bpmManager = None
        self.bvdata = None
        self._BVDataTask = None
        self.bkg_substraction_handler = None

        self.palette = self.init_palette()

        # initialize min max for image scaling
        # self.min_max = [0, 2**(self.ImageType2Bpp[_control_ref().image().getImageType()])]

        BasePostProcess.__init__(self, cl, name)
        self.init_device()

    @Core.DEB_MEMBER_FUNCT
    def init_device(self):
        BasePostProcess.init_device(self)
        if self.enable_tango_event:
            # enable event push for bvdata attribute
            self.set_change_event("bvdata", True, False)

    @Core.DEB_MEMBER_FUNCT
    def set_state(self, state):
        if state == PyTango.DevState.OFF:
            if self._softOp:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                if self.enable_tango_event:
                    self._BVDataTask.stop()
                    extOpt.delOp(self.BVDATA_TASK_NAME)
                extOpt.delOp(self.BPM_TASK_NAME)
                self._softOp = None
                self._bpmManager = None
                self._BVDataTask = None
        elif state == PyTango.DevState.ON:
            # 'set_state' is called many times, even with same state
            # so, we need to ensure tasks are not re-created for nothing
            # /!\ caution: in case of BVDataTask, a separate thread is
            # started and a weakref references the task from the thread,
            # the task cannot be re-created without stopping the thread
            # first, otherwise the weakref resolves to 'None' in the thread
            # causing exceptions.
            ctControl = _control_ref()
            extOpt = ctControl.externalOperation()
            if self.enable_bpm_calc and not self._bpmManager:
                self._softOp = extOpt.addOp(
                    Core.BPM, self.BPM_TASK_NAME, self._runLevel + 1
                )
                self._bpmManager = self._softOp.getManager()
            if self.enable_tango_event and not self._BVDataTask:
                self._BVDataTask = BVDataTask(self)
                handler = extOpt.addOp(
                    Core.USER_SINK_TASK, self.BVDATA_TASK_NAME, self._runLevel + 2
                )
                handler.setSinkTask(self._BVDataTask)

        PyTango.LatestDeviceImpl.set_state(self, state)

    def init_palette(self):
        greyscale_palette = numpy.zeros((65536, 3), dtype=numpy.uint8)
        greyscale_palette[:, 0] = numpy.linspace(0, 255, 65536)
        greyscale_palette[:, 1] = numpy.linspace(0, 255, 65536)
        greyscale_palette[:, 2] = numpy.linspace(0, 255, 65536)

        color_palette = numpy.zeros((65536, 3), dtype=numpy.uint8)
        color_palette[: 65536 // 4 :, 2] = 255
        color_palette[: 65536 // 4 :, 1] = numpy.linspace(0, 255, 65536 // 4)
        color_palette[65536 // 4 : 65536 // 2, 2] = numpy.linspace(255, 0, 65536 // 4)
        color_palette[65536 // 4 : 65536 // 2, 1] = 255
        color_palette[65536 // 2 : 65536 - 65536 // 4, 0] = numpy.linspace(
            0, 255, 65536 // 4
        )
        color_palette[65536 // 2 : 65536 - 65536 // 4, 1] = 255
        color_palette[65536 - 65536 // 4 : 65536, 0] = 255
        color_palette[65536 - 65536 // 4 : 65536, 1] = numpy.linspace(
            255, 0, 65536 // 4
        )

        return {"grey": greyscale_palette, "color": color_palette}

    # ------------------------------------------------------------------
    #    Read buffersize attribute
    # ------------------------------------------------------------------
    def read_buffersize(self, attr):
        value_read = self._bpmManager.historySize()
        attr.set_value(value_read)

    # ------------------------------------------------------------------
    #    Write buffersize attribute
    # ------------------------------------------------------------------
    def write_buffersize(self, attr):
        data = attr.get_write_value()
        self._bpmManager.resizeHistory(data)

    # ==================================================================
    #
    #    Bpm command methods
    #
    # ==================================================================
    def validate_number(self, x, fallback_value=-1, min_value=0, max_value=None):
        if x is None:
            return fallback_value
        if not numpy.isfinite(x):
            return fallback_value
        if numpy.isnan(x):
            return fallback_value
        if min_value is not None and x < min_value:
            return fallback_value
        if max_value is not None and x > max_value:
            return fallback_value
        return x

    def getResults(self, from_index=0):
        results = self._bpmManager.getHistory(from_index)
        result_array = numpy.zeros((len(results), 7))
        dim = _control_ref().image().getImageDim().getSize()
        max_width = dim.getWidth()
        max_height = dim.getHeight()
        for i, r in enumerate(results):
            result_array[i][0] = r.timestamp
            result_array[i][1] = self.validate_number(r.beam_intensity)
            result_array[i][2] = (
                self.validate_number(r.beam_center_x, max_value=max_width)
                * self.calibration[0]
            )
            result_array[i][3] = (
                self.validate_number(r.beam_center_y, max_value=max_height)
                * self.calibration[1]
            )
            result_array[i][4] = (
                self.validate_number(r.beam_fwhm_x, fallback_value=0)
                * self.calibration[0]
            )
            result_array[i][5] = (
                self.validate_number(r.beam_fwhm_y, fallback_value=0)
                * self.calibration[1]
            )
            result_array[i][6] = r.frameNumber
        return result_array.ravel()

    def GetPixelIntensity(self, coordinate):
        x = coordinate[0]
        y = coordinate[1]
        try:
            image = _control_ref().ReadImage()
            raw_image = image.buffer.copy()
            return int(raw_image[y][x])
        except:
            return -1

    def TakeBackground(self):
        ctControl = _control_ref()
        extOpt = ctControl.externalOperation()
        if self.bkg_substraction_handler is not None:
            extOpt.delOp("bkg")
        im = ctControl.ReadImage()
        self.bkg_substraction_handler = extOpt.addOp(
            Core.BACKGROUNDSUBSTRACTION, "bkg", self._runLevel
        )
        self.bkg_substraction_handler.setBackgroundImage(im)

    def ResetBackground(self):
        ctControl = _control_ref()
        extOpt = ctControl.externalOperation()
        if self.bkg_substraction_handler is not None:
            extOpt.delOp("bkg")
        self.bkg_substraction_handler = None

    def HasBackground(self):
        return self.bkg_substraction_handler is not None

    ##############
    # ==================================================================
    #
    #    BpmDeviceServer read/write attribute methods
    #
    # ==================================================================
    #
    def get_bpm_result(self, frameNumber=None, timestamp=None):
        if self.enable_bpm_calc:
            if frameNumber == None:
                t = time.time()
                result = self._bpmManager.getResult()
            else:
                t = timestamp
                result = self._bpmManager.getResult(0, frameNumber)

            dim = _control_ref().image().getImageDim().getSize()
            max_width = dim.getWidth()
            max_height = dim.getHeight()
            if result.errorCode != self._bpmManager.OK:
                x = -1
                y = -1
                intensity = -1
                fwhm_x = 0
                fwhm_y = 0
                max_intensity = 0
            else:
                x = self.validate_number(result.beam_center_x, max_value=max_width)
                x *= self.calibration[0]
                y = self.validate_number(result.beam_center_y, max_value=max_height)
                y *= self.calibration[1]
                intensity = self.validate_number(result.beam_intensity)
                fwhm_x = self.validate_number(result.beam_fwhm_x, fallback_value=0)
                fwhm_x *= self.calibration[0]
                fwhm_y = self.validate_number(result.beam_fwhm_y, fallback_value=0)
                fwhm_y *= self.calibration[1]
                max_intensity = self.validate_number(
                    result.max_pixel_value, fallback_value=0
                )
            try:
                profile_x = result.profile_x.buffer.astype(int)
            except Exception:
                profile_x = numpy.array([], dtype=int)
            try:
                profile_y = result.profile_y.buffer.astype(int)
            except Exception:
                profile_y = numpy.array([], dtype=int)
        else:
            t = time.time()
            x = -1
            y = -1
            intensity = -1
            fwhm_x = 0
            fwhm_y = 0
            max_intensity = 0
            profile_x = numpy.array([], dtype=int)
            profile_y = numpy.array([], dtype=int)

        acq_time = t
        result_array = [
            acq_time,
            x,
            y,
            intensity,
            fwhm_x,
            fwhm_y,
            max_intensity,
            profile_x,
            profile_y,
        ]
        return result_array

    def read_txy(self, attr):
        last_acq_time, last_x, last_y, _, _, _, _, _, _ = self.get_bpm_result()
        value = numpy.array([last_acq_time, last_x, last_y], numpy.double)
        attr.set_value(value)

    def read_x(self, attr):
        _, last_x, _, _, _, _, _, _, _ = self.get_bpm_result()
        attr.set_value(last_x)

    def read_y(self, attr):
        _, _, last_y, _, _, _, _, _, _ = self.get_bpm_result()
        attr.set_value(last_y)

    def read_intensity(self, attr):
        _, _, _, last_intensity, _, _, _, _, _ = self.get_bpm_result()
        attr.set_value(last_intensity)

    def read_fwhm_x(self, attr):
        _, _, _, _, last_fwhm_x, _, _, _, _ = self.get_bpm_result()
        attr.set_value(last_fwhm_x)

    def read_fwhm_y(self, attr):
        _, _, _, _, _, last_fwhm_y, _, _, _ = self.get_bpm_result()
        attr.set_value(last_fwhm_y)

    def read_max_intensity(self, attr):
        _, _, _, _, _, _, last_max_intensity, _, _ = self.get_bpm_result()
        attr.set_value(last_max_intensity)

    def read_proj_x(self, attr):
        _, _, _, _, _, _, _, last_proj_x, _ = self.get_bpm_result()
        attr.set_value(last_proj_x)

    def read_proj_y(self, attr):
        _, _, _, _, _, _, _, _, last_proj_y = self.get_bpm_result()
        attr.set_value(last_proj_y)

    def read_automaticaoi(self, attr):
        aoi = self._softOp.getTask().mRoiAutomatic
        attr.set_value(aoi)

    def write_automaticaoi(self, attr):
        aoi = attr.get_write_value()
        self._softOp.getTask().mRoiAutomatic = aoi

    def read_autoscale(self, attr):
        attr.set_value(self.autoscale)

    def write_autoscale(self, attr):
        data = attr.get_write_value()
        self.autoscale = data
        # update the property
        prop = {"autoscale": data}
        PyTango.Database().put_device_property(self.get_name(), prop)

    def is_autoscale_allowed(self, mode):
        return True

    def read_lut_method(self, attr):
        attr.set_value(self.lut_method)

    def write_lut_method(self, attr):
        data = attr.get_write_value()
        if data.upper() == "LINEAR" or data.upper() == "LOG":
            self.lut_method = data
            # update the property
            prop = {"lut_method": data}
            PyTango.Database().put_device_property(self.get_name(), prop)

        else:
            PyTango.Except.throw_exception(
                "WrongData",
                "Wrong value lut_method: {0}, use log or linear instead".format(data),
                "LimaCCD Class",
            )

    def is_lut_method_allowed(self, mode):
        return True

    def read_color_map(self, attr):
        attr.set_value(self.color_map)

    def write_color_map(self, attr):
        data = attr.get_write_value()
        self.color_map = data
        # update the property
        prop = {"color_map": data}
        PyTango.Database().put_device_property(self.get_name(), prop)

    def is_color_map_allowed(self, mode):
        return True

    def read_calibration(self, attr):
        if None not in self.calibration:
            attr.set_value(self.calibration)

    def write_calibration(self, attr):
        data = attr.get_write_value()
        self.calibration = data
        # update the property
        prop = {"calibration": data}
        PyTango.Database().put_device_property(self.get_name(), prop)

    def is_calibration_allowed(self, mode):
        return True

    def read_beammark(self, attr):
        if None not in self.beammark:
            attr.set_value(self.beammark)

    def write_beammark(self, attr):
        data = attr.get_write_value()
        self.beammark[0] = data[0]
        self.beammark[1] = data[1]
        # update the property
        prop = {"beammark": data}
        PyTango.Database().put_device_property(self.get_name(), prop)

    def is_beammark_allowed(self, mode):
        return True

    def read_jpeg_quality(self, attr):
        attr.set_value(self.jpeg_quality)

    def write_jpeg_quality(self, attr):
        data = attr.get_write_value()
        self.jpeg_quality = data
        # update the property
        prop = {"jpeg_quality": data}
        PyTango.Database().put_device_property(self.get_name(), prop)

    def is_jpeg_quality_allowed(self, mode):
        return True

    def read_bvdata(self, attr):
        self.bvdata = None
        self.bvdata_format = None
        self.bvdata, self.bvdata_format = construct_bvdata(self)

        attr.set_value(self.bvdata_format, self.bvdata)

    def read_min_max(self, attr):
        attr.set_value(self.min_max)

    def write_min_max(self, attr):
        data = attr.get_write_value()
        max = 2 ** (self.ImageType2Bpp[_control_ref().image().getImageType()])
        range = [0, max]
        # reset asked to default
        if data[0] == 0 and data[1] == 0:
            data[1] = max

        if data[0] > data[1]:
            PyTango.Except.throw_exception(
                "WrongData",
                "Wrong values min_max: {0}, max < min".format(data),
                "LimaCCD Class",
            )

        if data[0] > max or data[1] > max:
            PyTango.Except.throw_exception(
                "WrongData",
                "Wrong value min_max: {0}, out of range {1}".format(data, range),
                "LimaCCD Class",
            )
        self.min_max[0] = data[0]
        self.min_max[1] = data[1]
        # update the property
        prop = {"min_max": data}
        PyTango.Database().put_device_property(self.get_name(), prop)

    def is_min_max_allowed(self, mode):
        return True

    def read_return_bpm_profiles(self, attr):
        attr.set_value(self.return_bpm_profiles)

    def write_return_bpm_profiles(self, attr):
        data = attr.get_write_value()
        self.return_bpm_profiles = data
        # update the property
        prop = {"return_bpm_profiles": data}
        PyTango.Database().put_device_property(self.get_name(), prop)

    def is_return_bpm_profiles_allowed(self, mode):
        return True

    def read_enable_bpm_calc(self, attr):
        attr.set_value(self.enable_bpm_calc)

    def write_enable_bpm_calc(self, attr):
        flag = attr.get_write_value()
        self.enable_bpm_calc = bool(flag)

    def is_enable_bpm_calc_allowed(self, mode):
        return True


# ==================================================================
#
#    BpmClass class definition
#
# ==================================================================
class BpmDeviceServerClass(PyTango.DeviceClass):

    # 	 Class Properties
    class_property_list = {}

    # 	 Device Properties
    device_property_list = {
        "enable_tango_event": [
            PyTango.DevBoolean,
            "Enable or disable the push event on bvdata attribute",
            True,
        ],
        "calibration": [
            PyTango.DevVarDoubleArray,
            "Array containing calibX and calibY",
            [1.0, 1.0],
        ],
        "beammark": [
            PyTango.DevVarLongArray,
            "Array containing BeamMark positions (X,Y)",
            [0, 0],
        ],
        "lut_method": [
            PyTango.DevString,
            "LUT method for colormap conversion, linear/log",
            ["LINEAR"],
        ],
        "autoscale": [
            PyTango.DevBoolean,
            "Set true or false autoscaling to min/max",
            True,
        ],
        "color_map": [
            PyTango.DevBoolean,
            "Set true or false colored map (temperature)",
            False,
        ],
        "jpeg_quality": [PyTango.DevLong, "Set jpeg encoding quality from 1-100", 80],
        "return_bpm_profiles": [
            PyTango.DevBoolean,
            "return bpm profiles if True, otherwise the beammark profiles",
            True,
        ],
        "min_max": [
            PyTango.DevVarLongArray,
            "min/max value for manual scaling",
            [0, 65535],
        ],
        "enable_bpm_calc": [PyTango.DevBoolean, "Enable/Disable bpm calculation", True],
    }

    # 	 Command definitions
    cmd_list = {
        "getResults": [
            [PyTango.DevLong, "from frame number"],
            [PyTango.DevVarDoubleArray, "frame number,x,y"],
        ],
        "Start": [[PyTango.DevVoid, "Start Bpm device"], [PyTango.DevVoid, ""]],
        "Stop": [[PyTango.DevVoid, "Stop Bpm device"], [PyTango.DevVoid, ""]],
        "GetPixelIntensity": [
            [PyTango.DevVarLongArray, "pixel coordinate"],
            [PyTango.DevLong, "return intensity on last image"],
        ],
        "HasBackground": [
            [PyTango.DevVoid, "check if bpm has background"],
            [PyTango.DevBoolean, ""],
        ],
        "TakeBackground": [
            [PyTango.DevVoid, "Set a background"],
            [PyTango.DevVoid, ""],
        ],
        "ResetBackground": [
            [PyTango.DevVoid, "Reset background"],
            [PyTango.DevVoid, ""],
        ],
    }

    # 	 Attribute definitions
    attr_list = {
        "RunLevel": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "buffersize": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "txy": [[PyTango.DevDouble, PyTango.SPECTRUM, PyTango.READ, 3]],
        "x": [[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ]],
        "y": [[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ]],
        "automaticaoi": [[PyTango.DevBoolean, PyTango.SCALAR, PyTango.READ_WRITE]],
        "intensity": [[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ]],
        "max_intensity": [[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ]],
        "proj_x": [[PyTango.DevLong, PyTango.SPECTRUM, PyTango.READ, 4096]],
        "proj_y": [[PyTango.DevLong, PyTango.SPECTRUM, PyTango.READ, 4096]],
        "fwhm_x": [[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ]],
        "fwhm_y": [[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ]],
        "autoscale": [[PyTango.DevBoolean, PyTango.SCALAR, PyTango.READ_WRITE]],
        "lut_method": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE]],
        "color_map": [[PyTango.DevBoolean, PyTango.SCALAR, PyTango.READ_WRITE]],
        "bvdata": [[PyTango.DevEncoded, PyTango.SCALAR, PyTango.READ]],
        "calibration": [[PyTango.DevDouble, PyTango.SPECTRUM, PyTango.READ_WRITE, 2]],
        "beammark": [[PyTango.DevLong, PyTango.SPECTRUM, PyTango.READ_WRITE, 2]],
        "jpeg_quality": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "min_max": [[PyTango.DevULong64, PyTango.SPECTRUM, PyTango.READ_WRITE, 2]],
        "return_bpm_profiles": [
            [PyTango.DevBoolean, PyTango.SCALAR, PyTango.READ_WRITE]
        ],
        "enable_bpm_calc": [[PyTango.DevBoolean, PyTango.SCALAR, PyTango.READ_WRITE]],
    }

    # ------------------------------------------------------------------
    #    BpmDeviceServerClass Constructor
    # ------------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


class BVDataTask(Core.Processlib.SinkTaskBase):
    Core.DEB_CLASS(Core.DebModApplication, "BVDataTask")

    class _PushingThread(threading.Thread):
        Core.DEB_CLASS(Core.DebModApplication, "_PushingThread")

        def __init__(self, task):
            threading.Thread.__init__(self)
            self._task = weakref.ref(task)
            self.timestamp = time.time()

        def run(self):
            bpm_device = self._task()._bpm_device
            while self._task()._stop is False:

                with self._task()._lock:
                    while (
                        self._task()._new_frame_ready is False
                        and self._task()._stop is False
                    ):
                        self._task()._lock.wait()
                    if self._task()._stop:
                        break
                    self._task()._new_frame_ready = False

                dt = time.time() - self.timestamp
                if dt > 0.04:
                    bvdata, bvdata_format = construct_bvdata(bpm_device)
                    bpm_device.push_change_event("bvdata", bvdata_format, bvdata)
                    self.timestamp = time.time()

    def __init__(self, bpm_device):
        Core.Processlib.SinkTaskBase.__init__(self)
        self._bpm_device = bpm_device
        self._lock = threading.Condition()
        self._new_frame_ready = False
        self._stop = False
        self._pushing_event_thread = self._PushingThread(self)
        self._pushing_event_thread.start()

    def stop(self):
        with self._lock:
            self._stop = True
            self._lock.notify()
        self._pushing_event_thread.join()

    def process(self, data):
        with self._lock:
            # just inform pushing_thread of a new image
            self._new_frame_ready = True
            self._lock.notify()


# ------------------------------------------------------------------
# The BVDATA DevEncoded generator function
# Build the jpeg image and concatenate with bpm statistics
# It use PIL (pillow) for RGB conversion
# ------------------------------------------------------------------
def construct_bvdata(bpm):
    # just read the last image
    image = _control_ref().ReadImage()

    last_acq_time, last_x, last_y, last_intensity, last_fwhm_x, last_fwhm_y, last_max_intensity, last_proj_x, last_proj_y = bpm.get_bpm_result(
        image.frameNumber, image.timestamp
    )
    lima_roi = _control_ref().image().getRoi()
    roi_top_left = lima_roi.getTopLeft()
    roi_size = lima_roi.getSize()
    jpegFile = StringIO()

    # manual scaling: use the user image min/max intensity to filter
    if not bpm.autoscale:
        min_val = bpm.min_max[0]
        max_val = bpm.min_max[1]
        scale_image = image.buffer.clip(min_val, max_val)

    # auto scaling: use natural image intensity
    else:
        min_val = image.buffer.min()
        max_val = image.buffer.max()
        if max_val == 0:
            max_val = 1
        scale_image = image.buffer

    # logarithmic scaling
    if bpm.lut_method == "LOG":
        if min_val > 0:
            scale_image = numpy.log10(scale_image)
        else:
            scale_image = numpy.log10(scale_image.clip(1, None))
            min_val += 1
        min_val = numpy.log10(min_val)
        max_val = numpy.log10(max_val)

    # scale the image to the whole range 16bit before palette transformation for 0 to 65535
    if max_val == min_val:
        max_val += 1
    scaling = (2 ** 16 - 1.) / (max_val - min_val)
    scale_image = ((scale_image - min_val) * scaling).astype(numpy.uint16)

    # last transformation ot color or greys palette
    if bpm.color_map:
        img_buffer = bpm.palette["color"].take(scale_image, axis=0)
    else:
        img_buffer = bpm.palette["grey"].take(scale_image, axis=0)

    rgb = Image.fromarray(img_buffer, "RGB")
    if turbo_jpeg:
        jpegFile.write(
            turbo_jpeg.encode(
                numpy.asarray(rgb), pixel_format=TJPF_RGB, quality=bpm.jpeg_quality
            )
        )
    else:
        rgb.save(jpegFile, "jpeg", quality=bpm.jpeg_quality)

    raw_jpeg_data = jpegFile.getvalue()
    image_jpeg = base64.b64encode(raw_jpeg_data)
    if bpm.return_bpm_profiles:
        profile_x = last_proj_x.tobytes()
        profile_y = last_proj_y.tobytes()
    else:
        if bpm.beammark[0] >= image.buffer.shape[1]:
            profile_y = numpy.zeros(image.buffer.shape[0], dtype=numpy.uint64)
        else:
            profile_y = image.buffer[:, bpm.beammark[0]].astype(numpy.uint64)
        profile_y = profile_y.tobytes()

        if bpm.beammark[1] >= image.buffer.shape[0]:
            profile_x = numpy.zeros(image.buffer.shape[1], dtype=numpy.uint64)
        else:
            profile_x = image.buffer[bpm.beammark[1], :].astype(numpy.uint64)
        profile_x = profile_x.tobytes()

    bvdata_format = "dldddliiiidd%ds%ds%ds" % (
        len(profile_x),
        len(profile_y),
        len(image_jpeg),
    )
    bvdata = struct.pack(
        bvdata_format,
        last_acq_time,
        image.frameNumber,
        last_x,
        last_y,
        last_intensity,
        last_max_intensity,
        roi_top_left.x,
        roi_top_left.y,
        roi_size.getWidth(),
        roi_size.getHeight(),
        last_fwhm_x,
        last_fwhm_y,
        profile_x,
        profile_y,
        image_jpeg,
    )
    return bvdata, bvdata_format


_control_ref = None


def set_control_ref(control_class_ref):
    global _control_ref
    _control_ref = control_class_ref


def get_tango_specific_class_n_device():
    return BpmDeviceServerClass, BpmDeviceServer
