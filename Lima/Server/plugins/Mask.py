############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2022
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
from Lima.Server.plugins.Utils import getMaskFromFile, BasePostProcess
from Lima.Server import AttrHelper


class MaskDeviceServer(BasePostProcess):
    MASK_TASK_NAME = "MaskTask"
    Core.DEB_CLASS(Core.DebModApplication, "MaskDeviceServer")

    @Core.DEB_MEMBER_FUNCT
    def __init__(self, cl, name):
        self.__maskTask = None
        self.__maskFile = None
        self.__maskImage = Core.Processlib.Data()

        self.__Type = {"STANDARD": 0, "DUMMY": 1}

        BasePostProcess.__init__(self, cl, name)
        MaskDeviceServer.init_device(self)

    @Core.DEB_MEMBER_FUNCT
    def set_state(self, state):
        if state == PyTango.DevState.OFF:
            if self.__maskTask:
                self.__maskTask = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.MASK_TASK_NAME)
        elif state == PyTango.DevState.ON:
            if not self.__maskTask:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                self.__maskTask = extOpt.addOp(
                    Core.MASK, self.MASK_TASK_NAME, self._runLevel
                )
                self.__maskTask.setMaskImage(self.__maskImage)
        PyTango.LatestDeviceImpl.set_state(self, state)

    # ------------------------------------------------------------------
    #    Read MaskFile attribute
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_MaskFile(self, attr):
        if self.__maskFile is not None:
            attr.set_value(self.__maskFile)
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
    #    Mask command methods
    #
    # ==================================================================
    @Core.DEB_MEMBER_FUNCT
    def setMaskImage(self, filepath):
        """Set a mask image from a EDF filename.

        By default a mask data set to 0 will set the Lima data to 0.

        If the file header contains `masked_value` this convention can be
        chosen. This key can contain one of:

        - `zero`: Mask the data when the mask value is 0
                  (default Lima convention)
        - `nonzero`: Mask the data when the mask value is something else than 0
                     (default silx convention)
        """
        maskImage = getMaskFromFile(filepath)
        self.__maskImage = maskImage
        self.__maskFile = filepath
        if self.__maskTask:
            self.__maskTask.setMaskImage(self.__maskImage)

    @Core.DEB_MEMBER_FUNCT
    def setMaskFile(self, filepath):
        """ new command to fit with other correction plugin api
        """
        self.setMaskImage(filepath)

    # ------------------------------------------------------------------
    #    getAttrStringValueList command:
    #
    #    Description: return a list of authorized values if any
    #    argout: DevVarStringArray
    # ------------------------------------------------------------------
    def getAttrStringValueList(self, attr_name):
        return AttrHelper.get_attr_string_value_list(self, attr_name)

    def __getattr__(self, name):
        try:
            return BasePostProcess.__getattr__(self, name)
        except AttributeError:
            # ask the help to not store object ref (object attribute functions)
            # into  __dict__, mask task is recreated everytime the plugin is stopped/started
            return AttrHelper.get_attr_4u(
                self, name, self.__maskTask, update_dict=False
            )


class MaskDeviceServerClass(PyTango.DeviceClass):
    # 	 Class Properties
    class_property_list = {}

    # 	 Device Properties
    device_property_list = {}

    # 	 Command definitions
    cmd_list = {
        "setMaskImage": [
            [PyTango.DevString, "Full path of mask image file"],
            [PyTango.DevVoid, ""],
        ],
        "setMaskFile": [
            [PyTango.DevString, "Full path of mask image file"],
            [PyTango.DevVoid, ""],
        ],
        "getAttrStringValueList": [
            [PyTango.DevString, "Attribute name"],
            [PyTango.DevVarStringArray, "Authorized String value list"],
        ],
        "Start": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
        "Stop": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
    }

    # 	 Attribute definitions
    attr_list = {
        "RunLevel": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "type": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE]],
        "MaskFile": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE]],
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
    return MaskDeviceServerClass, MaskDeviceServer
