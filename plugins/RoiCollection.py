############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2021
# European Synchrotron Radiation Facility
# BP 220, Grenoble 38043
# FRANCE
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
import processlib
from Lima import Core
from Lima.Server.plugins.Utils import getDataFromFile,BasePostProcess
from Lima.Server import AttrHelper

def grouper(n, iterable, padvalue=None):
    return zip(*[itertools.chain(iterable, itertools.repeat(padvalue, n-1))]*n)


class AcqCallback(Core.SoftCallback):
    def __init__(self,container):
        Core.SoftCallback.__init__(self)
        self._container = container

    def prepare(self) :
        #New acquisition will start
        self._container._roiCollectionMgr.prepare()
        self._container._roiCollectionMgr.resetHistory()
        
#==================================================================
#   RoiCollection Class Description:
#
#
#==================================================================


class RoiCollectionDeviceServer(BasePostProcess) :

#--------- Add you global variables here --------------------------
    ROI_COLLECTION_TASK_NAME = "RoiCollectionTask"
#------------------------------------------------------------------
#    Device constructor
#------------------------------------------------------------------
    def __init__(self,cl, name):
        self._mgr = None
        self._roiCollectionMgr = Core.Processlib.Tasks.RoiCollectionManager()
        self._roiCollectionTask = Core.Processlib.Tasks.RoiCollectionTask(self._roiCollectionMgr)
        self._acq_callback = AcqCallback(self)
        
        BasePostProcess.__init__(self,cl,name)
        RoiCollectionDeviceServer.init_device(self)

    def set_state(self,state) :
        if(state == PyTango.DevState.OFF) :
            if(self.__roiCollectionMgr) :
                self.__roiCollectionMgr = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.ROI_COLLECTION_TASK_NAME)
        elif(state == PyTango.DevState.ON) :
            if not self.__roiCollectionMgr:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                self._mgr = extOpt.addOp(Core.USER_SINK_TASK,self.ROI_COLLECTION_TASK_NAME,
                                         self._runLevel)
                self._mgr.setSinkTask(self._task)
                self._mgr.registerCallback(self._acq_callback)
                
        PyTango.LatestDeviceImpl.set_state(self,state)

#------------------------------------------------------------------
#    Read BufferSize attribute
#------------------------------------------------------------------
    def read_BufferSize(self, attr):
        value_read = self.__roiCollectionMgr.historySize()
        attr.set_value(value_read)


#------------------------------------------------------------------
#    Write BufferSize attribute
#------------------------------------------------------------------
    def write_BufferSize(self, attr):
        data = attr.get_write_value()
        self.__roiCollectionMgr.resizeHistory(data)

#------------------------------------------------------------------
#    Read CounterStatus attribute
#------------------------------------------------------------------
    def read_CounterStatus(self, attr):
        value_read = self.__roiCollectionMgr.lastFrameNumber()
        attr.set_value(value_read)


#==================================================================
#
#    RoiCollection command methods
#
#==================================================================

    def setMaskFile(self,argin) :
        mask = getDataFromFile(*argin)
        self.__roiCollectionMgr.setMask(mask)

    def setRois(self,argin):
        if not len(argin) % 4:
            roi_list = ((x,y,width,height) for x,y,width,height in grouper(4,argin))
            self.__roiCollectionMgr.setRoi(roi_list)
        else:
            raise AttributeError('should be a vector as follow [x0,y0,width0,height0,...')
        
    def readSpectrum(self,argin) :
        result_counters = self.__roiCollectionMgr.getHistory(argin)
        if result_counters:
            list_size = len(result_counters)
            if list_size :
                spectrum_size = len(result_counters[0].spectrum)
                first_frame_id = result_counters[0].frameNumber
                
                returnArray = numpy.zeros(list_size * spectrum_size + 3,dtype = numpy.int)
                returnArray[0:3] = (list_size,spectrum_size,first_frame_id)
                indexArray = 3
                for result in peakResultCounterList:
                    returnArray[indexArray:indexArray+spectrum_size] = result.spectrum_size
                    indexArray += spectrum_size
                return returnArray
        return numpy.array([],dtype = numpy.int)

#==================================================================
#
#    RoiCollectionClass class definition
#
#==================================================================
class RoiCollectionDeviceServerClass(PyTango.DeviceClass):

    #	 Class Properties
    class_property_list = {
	}


    #	 Device Properties
    device_property_list = {
	}


    #	 Command definitions
    cmd_list = {
        'setMaskFile':
            [[PyTango.DevVarStringArray,"Full path of mask file"],
             [PyTango.DevVoid,""]],
        'setRois':
        [[PyTango.DevVarLongArray,"roi vector [x0,y0,width0,height0,x1,y1,width1,heigh1,...]"],
         [PyTango.DevVoid,""]],
         'readSpectrum':
            [[PyTango.DevLong,"from which frame"],
             [PyTango.DevVarLongArray,"number of spectrum,spectrum size,first frame id,spectrum0,spectrum1..."]],
	'Start':
            [[PyTango.DevVoid,""],
             [PyTango.DevVoid,""]],
	'Stop':
            [[PyTango.DevVoid,""],
             [PyTango.DevVoid,""]],
	}

    #	 Attribute definitions
    attr_list = {
	'BufferSize':
	    [[PyTango.DevLong,
	    PyTango.SCALAR,
	    PyTango.READ_WRITE]],
	'CounterStatus':
	    [[PyTango.DevLong,
	    PyTango.SCALAR,
	    PyTango.READ]],
	'RunLevel':
	    [[PyTango.DevLong,
	    PyTango.SCALAR,
	    PyTango.READ_WRITE]],
	}


#------------------------------------------------------------------
#    RoiCollectionDeviceServerClass Constructor
#------------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name);



_control_ref = None
def set_control_ref(control_class_ref) :
    global _control_ref
    _control_ref= control_class_ref

def get_tango_specific_class_n_device() :
   return RoiCollectionDeviceServerClass,RoiCollectionDeviceServer
