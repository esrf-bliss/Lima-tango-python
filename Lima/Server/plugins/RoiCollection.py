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

import itertools
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
    Core.DEB_CLASS(Core.DebModApplication, 'RoiCollectionDeviceServer')
    
#--------- Add you global variables here --------------------------
    ROI_COLLECTION_TASK_NAME = "RoiCollectionTask"
#------------------------------------------------------------------
#    Device constructor
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def __init__(self,cl, name):
        self._mgr = None
        self._maskFile = None
        self._maskData = None
        self._roiCollectionMgr = Core.Processlib.Tasks.RoiCollectionManager()
        self._roiCollectionTask = Core.Processlib.Tasks.RoiCollectionTask(self._roiCollectionMgr)
        self._acq_callback = AcqCallback(self)
        
        BasePostProcess.__init__(self,cl,name)
        RoiCollectionDeviceServer.init_device(self)

        # Set from properties
        self.setMaskFile(self.MaskFile)
        self._roiCollectionMgr.resizeHistory(self.BufferSize)
            
    @Core.DEB_MEMBER_FUNCT
    def set_state(self,state) :
        if(state == PyTango.DevState.OFF) :
            if(self._mgr) :
                self._mgr = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.ROI_COLLECTION_TASK_NAME)
        elif(state == PyTango.DevState.ON) :
            if not self._mgr:
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                self._mgr = extOpt.addOp(Core.USER_SINK_TASK,self.ROI_COLLECTION_TASK_NAME,
                                         self._runLevel)
                self._mgr.setSinkTask(self._roiCollectionTask)
                self._mgr.registerCallback(self._acq_callback)
                
        PyTango.LatestDeviceImpl.set_state(self,state)

#------------------------------------------------------------------
#    Read BufferSize attribute
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_BufferSize(self, attr):
        value_read = self._roiCollectionMgr.historySize()
        attr.set_value(value_read)


#------------------------------------------------------------------
#    Write BufferSize attribute
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def write_BufferSize(self, attr):
        data = attr.get_write_value()
        self._roiCollectionMgr.resizeHistory(data)
        
    def is_BufferSize_allowed(self,mode):
        return True
#------------------------------------------------------------------
#    Read CounterStatus attribute
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_CounterStatus(self, attr):
        value_read = self._roiCollectionMgr.lastFrameNumber()
        attr.set_value(value_read)

#------------------------------------------------------------------
#    Read MaskFile attribute
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_MaskFile(self, attr):
        if self._maskFile is not None:
            attr.set_value(self._maskFile)
        else:
            attr.set_value("")
        
#------------------------------------------------------------------
#    Write MaskFile attribute
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def write_MaskFile(self, attr):
        filename = attr.get_write_value()
        self.setMaskFile(filename)

    def is_MaskFile_allowed(self,mode):
        return True

#------------------------------------------------------------------
#    Read OverflowThreshold attribute
#------------------------------------------------------------------

    def read_OverflowThreshold(self,attr):
        value_read = self._roiCollectionMgr.getOverflowThreshold()
        attr.set_value(value_read)
        
#------------------------------------------------------------------
#    Write OverflowThreshold attribute
#------------------------------------------------------------------
    def write_OverflowThreshold(self,attr):
        overflowThl = attr.get_write_value()
        self._roiCollectionMgr.setOverflowThreshold(overflowThl)
        
    def is_OverflowThreshold_allowed(self,mode):
        return True

#==================================================================
#
#    RoiCollection command methods
#
#==================================================================

    @Core.DEB_MEMBER_FUNCT
    def setMaskFile(self,argin) :
        if len(argin):
           try:
               data = getMaskFromFile(argin)
           except:
               raise ValueError(f"Could read mask from {argin}")
           self._roiCollectionMgr.setMask(data)
           self._maskData = data
           self._maskFile = argin
        else:
           if self._maskData is not None:
               # reset the mask if needed
               if self._roiCollectionMgr is not None:
                  emptyData = Core.Processlib.Data()
                  self._roiCollectionMgr.setMask(emptyData)
           self._maskData = None
           self._maskFile = None

    @Core.DEB_MEMBER_FUNCT
    def clearAllRois(self):
        self._roiCollectionMgr.clearRois()
        
    @Core.DEB_MEMBER_FUNCT
    def setRois(self,argin):
        if not len(argin) % 4:
            roi_list = ((x,y,width,height) for x,y,width,height in grouper(4,argin))
            self._roiCollectionMgr.setRois(list(roi_list))
        else:
            raise AttributeError('should be a vector as follow [x0,y0,width0,height0,...')
        
    @Core.DEB_MEMBER_FUNCT
    def readSpectrum(self,argin) :
        result_counters = self._roiCollectionMgr.getHistory(argin)
        if result_counters:
            list_size = len(result_counters)
            if list_size and result_counters[0].spectrum is not None:
                spectrum_size = len(result_counters[0].spectrum)
                first_frame_id = result_counters[0].frameNumber
                
                returnArray = numpy.zeros(list_size * spectrum_size + 3,dtype = numpy.int)
                returnArray[0:3] = (list_size,spectrum_size,first_frame_id)
                indexArray = 3
                for result in result_counters:
                    returnArray[indexArray:indexArray+spectrum_size] = result.spectrum
                    indexArray += spectrum_size
                return returnArray
        return numpy.array([],dtype = numpy.int)

#==================================================================
#
#    RoiCollectionDeviceServerClass class definition
#
#==================================================================
class RoiCollectionDeviceServerClass(PyTango.DeviceClass):
    Core.DEB_CLASS(Core.DebModApplication, 'RoiCollectionDeviceServerClass')
    #	 Class Properties
    class_property_list = {
	}


    #	 Device Properties
    device_property_list = {
        'BufferSize':
        [PyTango.DevShort,
         "Rois buffer size",[256]],
        'MaskFile':
        [PyTango.DevString,
         "Mask file", ""],
    }


    #	 Command definitions
    cmd_list = {
        'setMaskFile':
        [[PyTango.DevVarStringArray,"Full path of mask file"],
         [PyTango.DevVoid,""]],
        'clearAllRois':
        [[PyTango.DevVoid,""],
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
        'MaskFile':
            [[PyTango.DevString,
            PyTango.SCALAR,
            PyTango.READ_WRITE]],
        'OverflowThreshold':
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
    @Core.DEB_MEMBER_FUNCT
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name);



_control_ref = None
def set_control_ref(control_class_ref) :
    global _control_ref
    _control_ref= control_class_ref

def get_tango_specific_class_n_device() :
   return RoiCollectionDeviceServerClass,RoiCollectionDeviceServer
