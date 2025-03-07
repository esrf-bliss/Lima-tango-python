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

import itertools
import weakref
import PyTango
import sys
import numpy
import processlib
from Lima import Core
from Lima.Server.plugins.Utils import getMaskFromFile, BasePostProcess


def grouper(n, iterable, padvalue=None):
    return zip(*[itertools.chain(iterable, itertools.repeat(padvalue, n - 1))] * n)


Roi2SpectrumTask = Core.Processlib.Tasks.Roi2SpectrumTask

# ==================================================================
#   Roi2spectrum Class Description:
#
#
# ==================================================================


class Roi2spectrumDeviceServer(BasePostProcess):

    # --------- Add you global variables here --------------------------
    ROI_SPECTRUM_TASK_NAME = "Roi2SpectrumTask"
    Core.DEB_CLASS(Core.DebModApplication, "Roi2spectrumDeviceServer")

    # ------------------------------------------------------------------
    #    Device constructor
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def __init__(self, cl, name):
        self.__roi2spectrumMgr = None
        self.__roiName2ID = {}
        self.__roiID2Name = {}
        self.__currentRoiId = 0
        self.__maskFile = None
        self.__maskData = None
        BasePostProcess.__init__(self, cl, name)
        Roi2spectrumDeviceServer.init_device(self)
        self.setMaskFile(self.MaskFile)

    @Core.DEB_MEMBER_FUNCT
    def set_state(self, state):
        if state == PyTango.DevState.OFF:
            if self.__roi2spectrumMgr:
                self.__roi2spectrumMgr = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.ROI_SPECTRUM_TASK_NAME)
        elif state == PyTango.DevState.ON:
            if not self.__roi2spectrumMgr:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                self.__roi2spectrumMgr = extOpt.addOp(
                    Core.ROI2SPECTRUM, self.ROI_SPECTRUM_TASK_NAME, self._runLevel
                )
                self.__roi2spectrumMgr.setBufferSize(int(self.BufferSize))
                if self.__maskData is not None:
                    self.__roi2spectrumMgr.setMask(self.__maskData)
            self.__roi2spectrumMgr.clearCounterStatus()

        PyTango.LatestDeviceImpl.set_state(self, state)

    # ------------------------------------------------------------------
    #    Read BufferSize attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_BufferSize(self, attr):
        attr.set_value(self.BufferSize)

    # ------------------------------------------------------------------
    #    Write BufferSize attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def write_BufferSize(self, attr):
        data = attr.get_write_value()
        self.BufferSize = int(data)
        if self.__roi2spectrumMgr is not None:
            self.__roi2spectrumMgr.setBufferSize(data)

    def is_BufferSize_allowed(self, mode):
        return True

    # ------------------------------------------------------------------
    #    Read CounterStatus attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_CounterStatus(self, attr):
        value_read = self.__roi2spectrumMgr.getCounterStatus()
        attr.set_value(value_read)

    # ------------------------------------------------------------------
    #    Read MaskFile attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_MaskFile(self, attr):
        if self._maskFile is not None:
            attr.set_value(self._maskFile)
        else:
            attr.set_value("")

    # ------------------------------------------------------------------
    #    Write MaskFile attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def write_MaskFile(self, attr):
        filename = attr.get_write_value()
        self.setMaskFile(filename)

    def is_MaskFile_allowed(self, mode):
        return True

    # ==================================================================
    #
    #    Roi2spectrum command methods
    #
    # ==================================================================
    @Core.DEB_MEMBER_FUNCT
    def addNames(self, argin):
        roi_id = []
        for roi_name in argin:
            if not roi_name in self.__roiName2ID:
                self.__roiName2ID[roi_name] = self.__currentRoiId
                self.__roiID2Name[self.__currentRoiId] = roi_name
                roi_id.append(self.__currentRoiId)
                self.__currentRoiId += 1
            else:
                roi_id.append(self.__roiName2ID[roi_name])
        return roi_id

    @Core.DEB_MEMBER_FUNCT
    def removeRois(self, argin):
        if self.__roi2spectrumMgr:
            self.__roi2spectrumMgr.removeRois(argin)
        for roi_name in argin:
            roi_id = self.__roiName2ID.pop(roi_name, None)
            self.__roiID2Name.pop(roi_id, None)

    @Core.DEB_MEMBER_FUNCT
    def setRois(self, argin):
        if self.__roi2spectrumMgr is None:
            raise RuntimeError("should start the device first")

        if not len(argin) % 5:
            roi_list = []
            for roi_id, x, y, width, height in grouper(5, argin):
                roi_name = self.__roiID2Name.get(roi_id, None)
                if roi_name is None:
                    raise RuntimeError("should call add method before setRoi")
                roi_list.append((roi_name.encode(), Core.Roi(x, y, width, height)))
            self.__roi2spectrumMgr.updateRois(roi_list)
        else:
            raise AttributeError(
                "should be a vector as follow [roi_id0,x0,y0,width0,height0,..."
            )

    @Core.DEB_MEMBER_FUNCT
    def getNames(self):
        if self.__roi2spectrumMgr is None:
            raise RuntimeError("should start the device first")
        return self.__roi2spectrumMgr.getNames()

    @Core.DEB_MEMBER_FUNCT
    def getRois(self, argin):
        if self.__roi2spectrumMgr is None:
            raise RuntimeError("should start the device first")
        roi_list = []
        rois_names = self.__roi2spectrumMgr.getRois()
        for roi_name in argin:
            for name, roi in rois_names:
                if name == roi_name:
                    break
            else:
                raise ValueError("Roi %s not defined yet" % roi_name)
            roi_id = self.__roiName2ID[roi_name]
            x, y = roi.getTopLeft().x, roi.getTopLeft().y
            w, h = roi.getSize().getWidth(), roi.getSize().getHeight()
            roi_list.append((roi_id, x, y, w, h))
        return list(itertools.chain(*roi_list))

    @Core.DEB_MEMBER_FUNCT
    def getRoiModes(self, argin):
        if self.__roi2spectrumMgr is None:
            raise RuntimeError("should start the device first")
        roi_mode_list = []
        rois_modes = self.__roi2spectrumMgr.getRoiModes()
        for roi_name in argin:
            for name, roi_mode in rois_modes:
                if name == roi_name:
                    break
            else:
                raise ValueError("Roi %s not defined yet" % roi_name)
            roi_mode_map = {
                Roi2SpectrumTask.COLUMN_SUM: "COLUMN_SUM",
                Roi2SpectrumTask.LINES_SUM: "LINES_SUM",
            }
            roi_mode_list.append(roi_mode_map[roi_mode])
        return roi_mode_list

    @Core.DEB_MEMBER_FUNCT
    def setRoiModes(self, argin):
        roi_mode_map = {
            "COLUMN_SUM": Roi2SpectrumTask.COLUMN_SUM,
            "LINES_SUM": Roi2SpectrumTask.LINES_SUM,
        }
        rois_modes = [(n, roi_mode_map[m]) for n, m in grouper(2, argin)]
        self.__roi2spectrumMgr.setRoiModes(rois_modes)

    @Core.DEB_MEMBER_FUNCT
    def clearAllRois(self):
        self.__roi2spectrumMgr.clearAllRois()

    @Core.DEB_MEMBER_FUNCT
    def setMaskFile(self, argin):
        if len(argin):
            try:
                data = getMaskFromFile(argin)
            except:
                raise ValueError(f"Could read mask from {argin}")
            self.__maskData = data
            self.__maskFile = argin
            if self.__roiCounterMgr is not None:
                self.__roi2spectrumMgr.setMask(self.__maskData)
        else:
            if self.__maskData is not None:
                # reset the mask if needed
                if self.__roiCounterMgr is not None:
                    emptyData = Core.Processlib.Data()
                    self.__roiCounterMgr.setMask(emptyData)
            self.__maskData = None
            self.__maskFile = None

    @Core.DEB_MEMBER_FUNCT
    def readImage(self, argin):
        roiId, fromImageId = argin
        roi_name = self.__roiID2Name.get(roiId, None)
        startImage, data = self.__roi2spectrumMgr.createImage(roi_name, fromImageId)
        # Overflow
        if fromImageId >= 0 and startImage != fromImageId:
            raise "Overrun ask id %d, given id %d (no more in memory" % (
                fromImageId,
                startImage,
            )

        # Check whether the spectrum is ready
        if data.buffer is None:
            return []
        else:
            self._data_cache = data  # Tango is not so beautiful
            return data.buffer.ravel()


# ==================================================================
#
#    Roi2spectrumClass class definition
#
# ==================================================================
class Roi2spectrumDeviceServerClass(PyTango.DeviceClass):

    # 	 Class Properties
    class_property_list = {}

    # 	 Device Properties
    device_property_list = {
        "BufferSize": [PyTango.DevShort, "Rois buffer size", [256]],
        "MaskFile": [PyTango.DevString, "Mask file", ""],
    }

    # 	 Command definitions
    cmd_list = {
        "addNames": [
            [PyTango.DevVarStringArray, "rois alias"],
            [PyTango.DevVarLongArray, "rois' id"],
        ],
        "removeRois": [
            [PyTango.DevVarStringArray, "rois alias"],
            [PyTango.DevVoid, ""],
        ],
        "setRois": [
            [
                PyTango.DevVarLongArray,
                "roi vector [roi_id0,x0,y0,width0,height0,roi_id1,x1,y1,width1,heigh1,...]",
            ],
            [PyTango.DevVoid, ""],
        ],
        "getRois": [
            [PyTango.DevVarStringArray, "rois alias"],
            [
                PyTango.DevVarLongArray,
                "roi vector [roi_id0,x0,y0,width0,height0,roi_id1,x1,y1,width1,heigh1,...]",
            ],
        ],
        "getNames": [[PyTango.DevVoid, ""], [PyTango.DevVarStringArray, "rois alias"]],
        "getRoiModes": [
            [PyTango.DevVarStringArray, "rois alias"],
            [PyTango.DevVarStringArray, "rois modes"],
        ],
        "setRoiModes": [
            [
                PyTango.DevVarStringArray,
                "roi mode vector [alias0,mode0,alias1,mode1,...]",
            ],
            [PyTango.DevVoid, ""],
        ],
        "setMaskFile": [
            [PyTango.DevString, "Full path of mask file"],
            [PyTango.DevVoid, ""],
        ],
        "clearAllRois": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
        "readImage": [
            [PyTango.DevVarLongArray, "[roiId,from which frame]"],
            [PyTango.DevVarLongArray, "The image"],
        ],
        "Start": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
        "Stop": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
    }

    # 	 Attribute definitions
    attr_list = {
        "BufferSize": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "MaskFile": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE]],
        "CounterStatus": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ]],
        "RunLevel": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
    }

    # ------------------------------------------------------------------
    #    Roi2spectrumDeviceServerClass Constructor
    # ------------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


_control_ref = None


def set_control_ref(control_class_ref):
    global _control_ref
    _control_ref = control_class_ref


def get_tango_specific_class_n_device():
    return Roi2spectrumDeviceServerClass, Roi2spectrumDeviceServer
