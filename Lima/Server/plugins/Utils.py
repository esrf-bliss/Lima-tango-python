############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2026
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


from Lima import Core
from Lima.Server import EdfFile


def getDataFromFile(filepath, index=0):
    try:
        datas = getDatasFromFile(filepath, index, index + 1)
        return datas[0]
    except:
        import traceback

        traceback.print_exc()
        return Core.Processlib.Data()  # empty


##@brief the function read all known data file
#
# @todo add more file format
def getDatasFromFile(filepath, fromIndex=0, toIndex=-1):
    returnDatas = []
    try:
        f = EdfFile.EdfFile(filepath)
        if toIndex < 0:
            toIndex = f.GetNumImages()
        for i in range(fromIndex, toIndex):
            a = f.GetData(i)
            header = f.GetHeader(i)
            rData = Core.Processlib.Data()
            rData.buffer = a
            try:
                rData.header.update(header)
            except TypeError as e:
                import traceback

                traceback.print_exc()
            returnDatas.append(rData)
    except:
        import traceback

        traceback.print_exc()
    finally:
        return returnDatas


def getMaskFromFile(filepath):
    """Returns a data object from filename.

    By default a mask data set to 0 will set the Lima data to 0.

    If the file header contains `masked_value` this convention can be
    chosen. This key can contain one of:

    - `zero`: Mask the data when the mask value is 0
              (default Lima convention)
    - `nonzero`: Mask the data when the mask value is something else than 0
                 (default silx convention)

    Arguments:
        filename: File name

    Returns:
        A Core.Processlib.Data object
    """
    maskImage = getDataFromFile(filepath)
    # Check masking convention
    masked_value = maskImage.header.get("masked_value")
    if masked_value not in [None, "zero", "nonzero"]:
        # Sanitize
        msg = "Header 'masked_value=%s' from file %s is unknown. Header skipped."
        print(msg % (masked_value, filepath))
        masked_value = None

    # Normalize the mask if needed
    if masked_value == "nonzero":
        # nexus and silx convention: mask != 0 means the data is masked (set to 0)
        maskImage.buffer = (maskImage.buffer == 0).astype("uint8")

    return maskImage


class BasePostProcess(PyTango.LatestDeviceImpl):
    def __init__(self, *args):
        self._runLevel = 0
        PyTango.LatestDeviceImpl.__init__(self, *args)

    def __getattr__(self, name):
        if name.startswith("is_") and name.endswith("_allowed"):
            self.__dict__[name] = self.__global_allowed
            return self.__global_allowed
        raise AttributeError("%s has no attribute %s" % (self.__class__.__name__, name))

    def __global_allowed(self, *args):
        return self.get_state() == PyTango.DevState.ON

    def is_RunLevel_allowed(self, mode):
        if PyTango.AttReqType.READ_REQ == mode:
            return True
        else:
            return self.get_state() == PyTango.DevState.OFF

    def is_set_state_allowed(self):
        return True

    def init_device(self):
        self.set_state(PyTango.DevState.OFF)
        self.get_device_properties(self.get_device_class())

    def Start(self):
        self.set_state(PyTango.DevState.ON)

    def Stop(self):
        self.set_state(PyTango.DevState.OFF)

    # ------------------------------------------------------------------
    #    Read RunLevel attribute
    # ------------------------------------------------------------------
    def read_RunLevel(self, attr):
        attr.set_value(self._runLevel)

    # ------------------------------------------------------------------
    #    Write RunLevel attribute
    # ------------------------------------------------------------------
    def write_RunLevel(self, attr):
        data = attr.get_write_value()
        self._runLevel = data
