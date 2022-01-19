############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2021
# European Synchrotron Radiation Facility
# CS40220 38043 Grenoble Cedex 9
# FRANCE
#
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

from Lima import Core
from Lima.Server.plugins.Utils import getDataFromFile, BasePostProcess


class FlatfieldDeviceServer(BasePostProcess):
    FLATFIELD_TASK_NAME = "FlatField"
    Core.DEB_CLASS(Core.DebModApplication, "FlatfieldDeviceServer")

    @Core.DEB_MEMBER_FUNCT
    def __init__(self, cl, name):
        self.__flatFieldTask = None
        self.__normalize = True
        self.__flatFieldFile = None

        self.__flatFieldImage = Core.Processlib.Data()

        BasePostProcess.__init__(self, cl, name)
        FlatfieldDeviceServer.init_device(self)

    @Core.DEB_MEMBER_FUNCT
    def set_state(self, state):
        if state == PyTango.DevState.OFF:
            if self.__flatFieldTask:
                self.__flatFieldTask = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.FLATFIELD_TASK_NAME)
        elif state == PyTango.DevState.ON:
            if not self.__flatFieldTask:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                self.__flatFieldTask = extOpt.addOp(
                    Core.FLATFIELDCORRECTION, self.FLATFIELD_TASK_NAME, self._runLevel
                )
                self.__flatFieldTask.setFlatFieldImage(
                    self.__flatFieldImage, self.__normalize
                )
        PyTango.LatestDeviceImpl.set_state(self, state)

    # ==================================================================
    #
    #    FlatfieldDeviceServer read/write attribute methods
    #
    # ==================================================================
    # ------------------------------------------------------------------
    #  normalize attribute
    # ------------------------------------------------------------------

    @Core.DEB_MEMBER_FUNCT
    def read_normalize(self, attr):
        attr.set_value(self.__normalize)

    @Core.DEB_MEMBER_FUNCT
    def write_normalize(self, attr):
        data = attr.get_write_value()
        self.__normalize = data

    def is_normalize_allowed(self, mode):
        if PyTango.AttReqType.READ_REQ == mode:
            return True
        else:
            return self.get_state() == PyTango.DevState.OFF

    # ------------------------------------------------------------------
    #    Read MaskFile attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_FlatFieldFile(self, attr):
        if self.__flatFieldFile is not None:
            attr.set_value(self.__flatFieldFile)
        else:
            attr.set_value("")

    # ------------------------------------------------------------------
    #    Write MaskFile attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def write_FlatFieldFile(self, attr):
        filename = attr.get_write_value()
        self.setFlatFieldFile(filename)

    def is_FlatFieldFile_allowed(self, mode):
        return True

    # ==================================================================
    #
    #    Mask command methods
    #
    # ==================================================================

    @Core.DEB_MEMBER_FUNCT
    def setFlatFieldImage(self, filepath):
        self.__flatFieldImage = getDataFromFile(filepath)
        self.__flatFieldFile = filepath
        if self.__flatFieldTask:
            self.__flatFieldTask.setFlatFieldImage(self.__flatFieldImage)

    @Core.DEB_MEMBER_FUNCT
    def setFlatFieldFile(self, filepath):
        """ new command to fit with other correction plugin api
        """
        self.setFlatFieldImage(filepath)


# ==================================================================
#
#    FlatfieldDeviceServerClass class definition
#
# ==================================================================
class FlatfieldDeviceServerClass(PyTango.DeviceClass):
    # 	 Class Properties
    class_property_list = {}

    # 	 Device Properties
    device_property_list = {}

    # 	 Command definitions
    cmd_list = {
        "setFlatFieldImage": [
            [PyTango.DevString, "Full path of flatfield image file"],
            [PyTango.DevVoid, ""],
        ],
        "setFlatFieldFile": [
            [PyTango.DevString, "Full path of flatfield image file"],
            [PyTango.DevVoid, ""],
        ],
        "Start": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
        "Stop": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
    }

    # 	 Attribute definitions
    attr_list = {
        "RunLevel": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "normalize": [[PyTango.DevBoolean, PyTango.SCALAR, PyTango.READ_WRITE]],
        "FlatFieldFile": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE]],
    }

    # ------------------------------------------------------------------
    #    RoiCounterDeviceServerClass Constructor
    # ------------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


_control_ref = None


def set_control_ref(control_class_ref):
    global _control_ref
    _control_ref = control_class_ref


def get_tango_specific_class_n_device():
    return FlatfieldDeviceServerClass, FlatfieldDeviceServer
