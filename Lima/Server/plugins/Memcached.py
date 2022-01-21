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

import weakref
import PyTango
import sys
import numpy
import json

import bloscpack
from collections import namedtuple
from pymemcache.client.base import Client

from Lima import Core
from Lima.Server.plugins.Utils import getDataFromFile, BasePostProcess
from Lima.Server import AttrHelper

# ==================================================================
#   MemcachedSinkTask SinkTask
# ==================================================================

Key = namedtuple("LImA", "detector acquisition frame")


def _key_repr(self):
    """Tune the representation of the namedtuple without spaces,
    because the memcached client wants no spaces in keys"""
    return "LImA(%s,%s,%s)" % self


Key.__repr__ = _key_repr


class MemcachedSinkTask(Core.Processlib.SinkTaskBase):
    def __init__(self, client, acquisitionID, detectorID=0, blosc_args=None):
        """
        :param client: A memcached client
        :param acquisitionID: acquisition identifier
        :param detectorID: detector identifier
        :param blosc_args: BloscArgs
        """
        super().__init__()
        self.__client = client
        self.detectorID = detectorID
        self.acquisitionID = acquisitionID
        self.blosc_args = blosc_args

    def process(self, img):
        """
        Process a frame
        """
        key = Key(self.detectorID, self.acquisitionID, img.frameNumber)
        metadata = {
            "timestamp": img.timestamp,
            "shape": img.buffer.shape,
            "dtype": img.buffer.dtype.name,
            "strides": img.buffer.strides,
        }
        raw = bloscpack.pack_bytes_to_bytes(
            img.buffer.data, metadata=metadata, blosc_args=self.blosc_args
        )
        self.__client.set(str(key), raw)


# ==================================================================
#   Memcached Class Description:
#
#
# ==================================================================


class MemcachedDeviceServer(BasePostProcess):

    # --------- Add you global variables here --------------------------
    MEMCACHED_TASK_NAME = "MemcachedTask"

    # ------------------------------------------------------------------
    #    Device constructor
    # ------------------------------------------------------------------
    def __init__(self, cl, name):
        self.__memcachedOpInstance = None
        self.__memcacheTask = None
        self.__client = None
        super().__init__(cl, name)
        self.init_device()
        self.get_device_properties(self.get_device_class())

    def set_state(self, state):
        if state == PyTango.DevState.OFF:
            if self.__memcachedOpInstance:
                self.__memcachedOpInstance = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.MEMCACHED_TASK_NAME)
                self.__memcacheTask = None
                self.__client = None
        elif state == PyTango.DevState.ON:
            if not self.__memcachedOpInstance:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                self.__memcachedOpInstance = extOpt.addOp(
                    Core.USER_SINK_TASK, self.MEMCACHED_TASK_NAME, self._runLevel
                )
                self.__client = Client((self.ServerIP, self.ServerPort))

                # Get detector model
                hw = ctControl.hwInterface()
                detinfo = hw.getHwCtrlObj(Core.HwCap.DetInfo)
                detectorID = detinfo.getDetectorModel()

                # Get image size
                img = ctControl.image()
                frame_dim = img.getImageDim()
                img_type = frame_dim.getImageType()

                # Prepare BloscArgs
                blosc_args = bloscpack.BloscArgs(
                    frame_dim.getImageTypeDepth(img_type),
                    self.CompressionLevel,
                    self.CompressionShuffle,
                    self.CompressionName,
                )

                # Create and set MemcachedSinkTask
                self.__memcacheTask = MemcachedSinkTask(
                    self.__client, self.AcquisitionID, detectorID, blosc_args
                )
                self.__memcachedOpInstance.setSinkTask(self.__memcacheTask)

        PyTango.LatestDeviceImpl.set_state(self, state)

    # ------------------------------------------------------------------
    #    Read MemcachedStats attribute
    # ------------------------------------------------------------------
    def read_MemcachedStats(self, attr):
        stats = self.__client.stats()
        decoded = {}
        for k, v in stats.items():
            if isinstance(k, bytes):
                k = k.decode()
            if isinstance(v, bytes):
                v = v.decode()
            decoded[k] = v
        # print(type(stats))
        print(decoded)
        # str = "".join(['%s = %s\n' % (str(key), str(value)) for (key, value) in stats.items()])
        attr.set_value(
            json.dumps(decoded, sort_keys=True, indent=4, separators=(",", ": "))
        )

    # ------------------------------------------------------------------
    #    Read MemcachedVersion attribute
    # ------------------------------------------------------------------
    def read_MemcachedVersion(self, attr):
        version = self.__client.version()
        attr.set_value(version)

    # ------------------------------------------------------------------
    #    Read AcquisitionID attribute
    # ------------------------------------------------------------------
    def read_AcquisitionID(self, attr):
        attr.set_value(self.__memcacheTask.acquisitionID)

    # ------------------------------------------------------------------
    #    Write AcquisitionID attribute
    # ------------------------------------------------------------------
    def write_AcquisitionID(self, attr):
        self.__memcacheTask.acquisitionID = attr.get_write_value()

    # ------------------------------------------------------------------
    #    Read CompressionName attribute
    # ------------------------------------------------------------------
    def read_CompressionName(self, attr):
        attr.set_value(self.CompressionName)

    # ------------------------------------------------------------------
    #    Write CompressionName attribute
    # ------------------------------------------------------------------
    def write_CompressionName(self, attr):
        self.CompressionName = attr.get_write_value()

    # ------------------------------------------------------------------
    #    Read CompressionLevel attribute
    # ------------------------------------------------------------------
    def read_CompressionLevel(self, attr):
        attr.set_value(self.CompressionLevel)

    # ------------------------------------------------------------------
    #    Write CompressionLevel attribute
    # ------------------------------------------------------------------
    def write_CompressionLevel(self, attr):
        self.CompressionLevel = attr.get_write_value()

    # ------------------------------------------------------------------
    #    Read CompressionShuffle attribute
    # ------------------------------------------------------------------
    def read_CompressionShuffle(self, attr):
        attr.set_value(self.CompressionShuffle)

    # ------------------------------------------------------------------
    #    Write CompressionShuffle attribute
    # ------------------------------------------------------------------
    def write_CompressionShuffle(self, attr):
        self.CompressionShuffle = attr.get_write_value()

    # ==================================================================
    #
    #    Memcached command methods
    #
    # ==================================================================

    def FlushAll(self):
        if self.__client is None:
            raise RuntimeError("Should start the device first")

        self.__client.flush_all()


# ==================================================================
#
#    MemcachedClass class definition
#
# ==================================================================
class MemcachedDeviceServerClass(PyTango.DeviceClass):

    # 	 Class Properties
    class_property_list = {}

    # 	 Device Properties
    device_property_list = {
        "ServerIP": [PyTango.DevString, "IP of the memcached server", ["127.0.0.1"]],
        "ServerPort": [PyTango.DevLong, "Port of the memcached server", [11211]],
        "AcquisitionID": [
            PyTango.DevString,
            "Default acquisition ID",
            ["beamline-camera-time"],
        ],
        "CompressionName": [PyTango.DevString, "Default compression name", ["lz4"]],
        "CompressionLevel": [PyTango.DevLong, "Default compression level [0-9]", [7]],
        "CompressionShuffle": [
            PyTango.DevLong,
            "Default pre-compression data shuffling [0-2]",
            [1],
        ],
    }

    # 	 Command definitions
    cmd_list = {
        "Start": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
        "Stop": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
        "FlushAll": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
    }

    # 	 Attribute definitions
    attr_list = {
        "AcquisitionID": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE]],
        "CompressionName": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE]],
        "CompressionLevel": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "CompressionShuffle": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "MemcachedStats": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ]],
        "MemcachedVersion": [[PyTango.DevString, PyTango.SCALAR, PyTango.READ]],
        "RunLevel": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
    }

    # ------------------------------------------------------------------
    #    MemcachedDeviceServerClass Constructor
    # ------------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


_control_ref = None


def set_control_ref(control_class_ref):
    global _control_ref
    _control_ref = control_class_ref


def get_tango_specific_class_n_device():
    return MemcachedDeviceServerClass, MemcachedDeviceServer
