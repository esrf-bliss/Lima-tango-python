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
import os
import PyTango

from Lima import Core
from Lima.Server.plugins.Utils import getDataFromFile,BasePostProcess

class BackgroundSubstractionDeviceServer(BasePostProcess) :
    BACKGROUND_TASK_NAME = 'BackGroundTask'
    GET_BACKGROUND_IMAGE = "TMP_GET_BACKGROUND_IMAGE"
    Core.DEB_CLASS(Core.DebModApplication,'BackgroundSubstractionDeviceServer')
    
    @Core.DEB_MEMBER_FUNCT
    def __init__(self,cl,name) :
        self.__background_op = None
        self.__backgroundFile = None
        self.__backgroundImage = Core.Processlib.Data()
        self.get_device_properties(self.get_device_class())
        self.__deleteDarkAfterRead = False
        self.__offset = 0
        
        BasePostProcess.__init__(self,cl,name)
        BackgroundSubstractionDeviceServer.init_device(self)

    @Core.DEB_MEMBER_FUNCT
    def set_state(self,state) :
        if(state == PyTango.DevState.OFF) :
            if(self.__background_op) :
                self.__background_op = None
                self.__get_image_op = None
                ctControl = _control_ref()
                extOpt = ctControl.externalOperation()
                extOpt.delOp(self.BACKGROUND_TASK_NAME)
                extOpt.delOp(self.GET_BACKGROUND_IMAGE)
        elif(state == PyTango.DevState.ON) :
            if not self.__background_op:
                try:
                  ctControl = _control_ref()
                  extOpt = ctControl.externalOperation()

                  # first create and add the task to update the background_image at level runLevel
                  # This task update the image only on demand from takeNextAcquisitionAsBackground() command
                  self.__get_image_op = extOpt.addOp(Core.USER_SINK_TASK,self.GET_BACKGROUND_IMAGE,
                                           self._runLevel)
                  self.__get_image_task = GetBackgroundImageTask(self,_control_ref)
                  self.__get_image_op.setSinkTask(self.__get_image_task)

                  # now add the background correction task at level runLevel+1
                  self.__background_op = extOpt.addOp(Core.BACKGROUNDSUBSTRACTION,
                                                       self.BACKGROUND_TASK_NAME,
                                                       self._runLevel+1)
                  self.__background_op.setBackgroundImage(self.__backgroundImage)
                  if self.__offset :
                      self.__background_op.setOffset(self.__offset)
                except:
                    self.__offset = 0
                    import traceback
                    traceback.print_exc()
                    return
        PyTango.LatestDeviceImpl.set_state(self,state)

        
    @Core.DEB_MEMBER_FUNCT
    def read_delete_dark_after_read(self,attr) :
        attr.set_value(self.__deleteDarkAfterRead)

    @Core.DEB_MEMBER_FUNCT
    def write_delete_dark_after_read(self,attr) :
        data = attr.get_write_value()
        self.__deleteDarkAfterRead = data

    def is_delete_dark_after_read_allowed(self,mode):
        return True

    @Core.DEB_MEMBER_FUNCT
    def read_offset(self,attr) :
        attr.set_value(self.__offset)

    @Core.DEB_MEMBER_FUNCT
    def write_offset(self,attr) :
        offset = attr.get_write_value()
        self.__offset = offset
        if self.__background_op:
            try:
                self.__background_op.setOffset(offset)
            except AttributeError:
                self.__offset = 0
                raise
            
    def is_offset_allowed(self,mode):
        return True

#------------------------------------------------------------------
#    Read MaskFile attribute
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def read_BackgroundFile(self, attr):
        if self.__backgroundFile is not None:
            attr.set_value(self.__backgroundFile)
        else:
            attr.set_value("")
        
#------------------------------------------------------------------
#    Write MaskFile attribute
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def write_BackgroundFile(self, attr):
        filename = attr.get_write_value()
        self.setBackgroundImageFile(filename)

    def is_BackgroundFile_allowed(self,mode):
        return True

#==================================================================
#
#    Background command methods
#
#==================================================================

    @Core.DEB_MEMBER_FUNCT
    def setBackgroundImage(self,filepath) :
        deb.Param('filepath=%s' % filepath)
        image = getDataFromFile(filepath)
        self.__backgroundFile = filepath
        if self.__deleteDarkAfterRead:
            os.unlink(filepath)
        self._setBackgroundImage(image)

    def _setBackgroundImage(self,image):
        self.__backgroundImage = image
        if(self.__background_op) :
            self.__background_op.setBackgroundImage(image)

    @Core.DEB_MEMBER_FUNCT
    def setBackgroundFile(self,filepath) :
        """ new command to fit with other correction plugin api
        """
        self.setBackgroundImage(filepath)

    @Core.DEB_MEMBER_FUNCT
    def takeNextAcquisitionAsBackground(self):
        self.__get_image_task.updateBackgroundImage()
        

class GetBackgroundImageTask(Core.Processlib.SinkTaskBase):
    def __init__(self,cnt,control_ref):
        Core.Processlib.SinkTaskBase.__init__(self)
        self.__control_ref = control_ref
        ctControl = _control_ref()
        saving = ctControl.saving()
        self.__cnt = cnt
        self.__update_background_image = False
        
    def updateBackgroundImage(self):
        self.__update_background_image = True
        
    def process(self,data):
        if self.__update_background_image:
            background = Core.Processlib.Data()
            background.buffer = data.buffer
            self.__cnt._setBackgroundImage(background)
            self.__update_background_image = False
        
        
class BackgroundSubstractionDeviceServerClass(PyTango.DeviceClass) :
        #	 Class Properties
    class_property_list = {
	}


    #	 Device Properties
    device_property_list = {
	}


    #	 Command definitions
    cmd_list = {
        'setBackgroundImage':
        [[PyTango.DevString,"Full path of background image file"],
         [PyTango.DevVoid,""]],
        'setBackgroundFile':
        [[PyTango.DevString,"Full path of background image file"],
         [PyTango.DevVoid,""]],
        'takeNextAcquisitionAsBackground':
        [[PyTango.DevVoid,""],
         [PyTango.DevVoid,""]],
	'Start':
	[[PyTango.DevVoid,""],
	 [PyTango.DevVoid,""]],
	'Stop':
	[[PyTango.DevVoid,""],
	 [PyTango.DevVoid,""]],
    }


    #	 Attribute definitions
    attr_list = {
	'RunLevel':
	[[PyTango.DevLong,
	  PyTango.SCALAR,
	  PyTango.READ_WRITE]],
	'delete_dark_after_read':
	[[PyTango.DevBoolean,
	  PyTango.SCALAR,
	  PyTango.READ_WRITE]],
        'offset':
        [[PyTango.DevLong,
          PyTango.SCALAR,
          PyTango.READ_WRITE]],
        'BackgroundFile':
        [[PyTango.DevString,
          PyTango.SCALAR,
          PyTango.READ_WRITE]],
	}


#------------------------------------------------------------------
#    RoiCounterDeviceServerClass Constructor
#------------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name);

_control_ref = None
def set_control_ref(control_class_ref) :
    global _control_ref
    _control_ref= control_class_ref

def get_tango_specific_class_n_device() :
   return BackgroundSubstractionDeviceServerClass,BackgroundSubstractionDeviceServer
