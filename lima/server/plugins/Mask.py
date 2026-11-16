############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2026
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
import tango
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command

from lima import core
from lima.server.plugins.Utils import getMaskFromFile
from lima.server import AttrHelper


class MaskDeviceServer(Device):
    MASK_TASK_NAME = "MaskTask"
    core.DEB_CLASS(core.DebModule.DebModApplication, "MaskDeviceServer")

    @core.DEB_MEMBER_FUNCT
    def init_device(self):
        # NOTE: not a bare super() call - see the mapping guide, DEB_MEMBER_FUNCT
        # rebuilds the function object and chokes on the implicit __class__ cell
        # that a zero-arg super() creates.
        Device.init_device(self)
        self._run_level = 0
        self._mask_task = None
        self._mask_file = None
        self._mask_image = core.Processlib.Data()
        self.__Type = {
            "STANDARD": core.SoftOpMask.Type.STANDARD,
            "DUMMY": core.SoftOpMask.Type.DUMMY,
        }
        self.set_state(DevState.OFF)

    @core.DEB_MEMBER_FUNCT
    def set_state(self, state):
        if state == DevState.OFF:
            if self._mask_task:
                self._mask_task = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.MASK_TASK_NAME)
        elif state == DevState.ON:
            if not self._mask_task:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                self._mask_task = extOpt.addOp(
                    core.SoftOpId.MASK, self.MASK_TASK_NAME, self._run_level
                )
                self._mask_task.setMaskImage(self._mask_image)
        Device.set_state(self, state)

    # ------------------------------------------------------------------
    #    RunLevel attribute
    # ------------------------------------------------------------------
    @attribute(dtype=int, access=AttrWriteType.READ_WRITE)
    def RunLevel(self):
        return self._run_level

    @RunLevel.setter
    def RunLevel(self, value):
        self._run_level = value

    def is_RunLevel_allowed(self, req_type):
        if req_type == tango.AttReqType.READ_REQ:
            return True
        return self.get_state() == DevState.OFF

    # ------------------------------------------------------------------
    #    MaskFile attribute
    # ------------------------------------------------------------------
    @attribute(dtype=str, access=AttrWriteType.READ_WRITE)
    @core.DEB_MEMBER_FUNCT
    def MaskFile(self):
        return self._mask_file if self._mask_file is not None else ""

    @MaskFile.setter
    @core.DEB_MEMBER_FUNCT
    def MaskFile(self, filename):
        self.setMaskFile(filename)

    def is_MaskFile_allowed(self, req_type):
        return True

    # ------------------------------------------------------------------
    #    type attribute
    # ------------------------------------------------------------------
    @attribute(dtype=str, access=AttrWriteType.READ_WRITE)
    def type(self):
        value = self._mask_task.getType()
        return AttrHelper.getDictKey(self.__Type, value)

    @type.setter
    def type(self, name):
        value = AttrHelper.getDictValue(self.__Type, name.upper())
        if value is None:
            tango.Except.throw_exception(
                "WrongData", "Wrong value type: %s" % name.upper(), "LimaCCD Class"
            )
        self._mask_task.setType(value)

    def is_type_allowed(self, req_type):
        return self.get_state() == DevState.ON

    # ==================================================================
    #    Mask command methods
    # ==================================================================
    @command(dtype_in=str)
    @core.DEB_MEMBER_FUNCT
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
        self._mask_image = maskImage
        self._mask_file = filepath
        if self._mask_task:
            self._mask_task.setMaskImage(self._mask_image)

    @command(dtype_in=str)
    @core.DEB_MEMBER_FUNCT
    def setMaskFile(self, filepath):
        """new command to fit with other correction plugin api"""
        self.setMaskImage(filepath)

    # ------------------------------------------------------------------
    #    getAttrStringValueList command:
    #
    #    Description: return a list of authorized values if any
    #    argout: DevVarStringArray
    # ------------------------------------------------------------------
    @command(dtype_in=str, dtype_out=(str,))
    def getAttrStringValueList(self, attr_name):
        return AttrHelper.get_attr_string_value_list(self, attr_name)

    @command
    def Start(self):
        self.set_state(DevState.ON)

    @command
    def Stop(self):
        self.set_state(DevState.OFF)


_control_ref = None


def set_control_ref(control_class_ref):
    global _control_ref
    _control_ref = control_class_ref


def get_tango_specific_class_n_device():
    return MaskDeviceServer.TangoClassClass, MaskDeviceServer
