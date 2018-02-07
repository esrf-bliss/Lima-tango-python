############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2015
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
#=============================================================================
#
# file :        Pixirad.py
#
# description : Python source for the Pixirad and its commands. 
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                Pilatus are implemented in this file.
#
# project :     TANGO Device Server
#
# copyleft :    European Synchrotron Radiation Facility
#               BP 220, Grenoble 38043
#               FRANCE
#
#=============================================================================
#         (c) - Bliss - ESRF
#=============================================================================
#
import PyTango
import  os

from Lima import Core
from Lima import Pixirad as PixiradModule
# import some useful helpers to create direct mapping between tango attributes
# and Lima APIs.
from Lima.Server import AttrHelper

class Pixirad(PyTango.Device_4Impl):
    Core.DEB_CLASS(Core.DebModApplication, 'LimaCCDs')
    
    
class Pixirad(PyTango.Device_4Impl):
    Core.DEB_CLASS(Core.DebModApplication, 'LimaCCDs')
    #Core.DEB_CLASS(Core.DebModApplication, 'Pixirad')
    

#------------------------------------------------------------------
#    Device constructor
#------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def __init__(self,cl, name) :
#
        PyTango.Device_4Impl.__init__(self,cl, name)
### #TOUT METTRE EN MINUSCULE ############# 

### TODO: Decide if we keep this exposed to the tango interface.                            
                            
                            #ENUM
                            
        self.__DeadTimeFreeMode = {'DEAD_TIME_FREE_MODE_OFF' : PixiradModule.Camera.DeadTimeFreeModeOFF, \
                                   'DEAD_TIME_FREE_MODE_ON' : PixiradModule.Camera.DeadTimeFreeModeON};
	
        self.__SensorConfigNBI  = {'SENSOR_CONFIG_NBI_OFF' : PixiradModule.Camera.SensorConfigNBI_OFF, \
                                   'SENSOR_CONFIG_NBI_ON' : PixiradModule.Camera.SensorConfigNBI_ON};
	
        self.__SensorConfigASIC = {'PII'  : PixiradModule.Camera.PII, \
                                   'PIII' : PixiradModule.Camera.PIII};
                            
        self.__SensorConfigHybrid = {'CDTE' : PixiradModule.Camera.CDTE, \
                                     'GAAS' : PixiradModule.Camera.GAAS};
                            
        self.__SensorConfigBuild = {'PX1' : PixiradModule.Camera.PX1, \
                                    'PX2' : PixiradModule.Camera.PX2, \
                                    'PX8' : PixiradModule.Camera.PX8};
                            
        #self.__RunConfigMode = {'DATA' : PixiradModule.Camera.DATA, \
                             #'COLLECT_FLAT' : PixiradModule.Camera.COLLECT_FLAT,\
                             #'SUMMED_DATA' : PixiradModule.Camera.SUMMED_DATA, \
                             #'SUMMED_COLLECT_FLAT' : PixiradModule.Camera.SUMMED_COLLECT_FLAT};
                            
        self.__CoolingMode = {'COOLING_OFF' : PixiradModule.Camera.COOLING_OFF, \
                              'COOLING_ON'  : PixiradModule.Camera.COOLING_ON};
                            
        self.__HVBiaisPower = {'HV_OFF' : PixiradModule.Camera.HV_OFF, \
                               'HV_ON'  : PixiradModule.Camera.HV_ON  };
                            
        self.__HVMode = {'AUTOHV'    : PixiradModule.Camera.AUTOHV, \
                         'AUTOHV_LC' : PixiradModule.Camera.AUTOHV_LC,\
                         'STDHV'     : PixiradModule.Camera.STDHV };
                            
        self.__ColorMode = { 'COLMODE_1COL0' : PixiradModule.Camera.COLMODE_1COL0, \
                             'COLMODE_2COL'  : PixiradModule.Camera.COLMODE_2COL,\
                             'COLMODE_1COL1' : PixiradModule.Camera.COLMODE_1COL1,\
                             'COLMODE_DTF'   : PixiradModule.Camera.COLMODE_DTF, \
                             'COLMODE_4COL'  : PixiradModule.Camera.COLMODE_4COL};


        self.__SyncOutFunction = {'SHUTTER' : PixiradModule.Camera.SHUTTER,
                                  'RODONE'  : PixiradModule.Camera.RODONE,
                                  'READ'    : PixiradModule.Camera.READ};

        self.__TrsfMode = {'UNMOD' : PixiradModule.Camera.UNMOD,
                           'UNMODH'  : PixiradModule.Camera.UNMODH,
                           'MOD'    : PixiradModule.Camera.MOD};

        self.__HybridMode = {'CDTE' : PixiradModule.Camera.CDTE,
                             'GAAS'  : PixiradModule.Camera.GAAS};

        self.__Polarity = { 'POS' : PixiradModule.Camera.POS,
                            'NEG' : PixiradModule.Camera.NEG};

	#__Attribute2FunctionBase		????    
	  
        self.init_device()
        
        
       
############## DESTRUCTOR ###################
    def delete_device(self):
        # Detruire camera et HWinterface ?
        pass

############## INIT ###################
    @Core.DEB_MEMBER_FUNCT
    def init_device(self):
        self.set_state(PyTango.DevState.ON)
        # Load the properties
        self.get_device_properties(self.get_device_class())

        # Apply property to the attributes
        ### Default Values
        
        #_PixiradInterface.setConfigBuild(self.__ConfigBuild[self.PX8])
        #_PixiradInterface.setSensorConfigHybrid(self.__SensorConfigHybrid[self.CDTE])




############## RW Attributes methods ###################
### Call directly set/get 
    def __getattr__(self,name) :      
        try:  
            return AttrHelper.get_attr_4u(self, name, _PixiradInterface)
        except:
            return AttrHelper.get_attr_4u(self, name, _PixiradCamera)

        

############## COMMANDS ###################
    @Core.DEB_MEMBER_FUNCT
    def getAttrStringValueList(self, attr_name):
            return AttrHelper.get_attr_string_value_list(self, attr_name)

class PixiradClass(PyTango.DeviceClass):

    class_property_list = {}

    device_property_list = {
        'ip_address':
        [PyTango.DevString,
         "IP Adress of the detector.",[]],
        'port_number':
        [PyTango.DevShort,
         "port number for detector (DAQ commands)",[]],
        'initial_model':
        [PyTango.DevString,
         "Model type PX1, PX8",[]]
        }

    cmd_list = {
        'getAttrStringValueList':
        [[PyTango.DevString, "Attribute name"],
         [PyTango.DevVarStringArray, "Authorized String value list"]],
        }

    attr_list = {
        'high_threshold0':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"High Energy threshold 0",
             'unit':"KeV",
             'format':"%5.2f",
             'description':"High Energy threshold 0 (KeV)",
         }]  ,
        'low_threshold0':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"Low Energy threshold 0",
             'unit':"KeV",
             'format':"%5.2f",
             'description':"Low Energy threshold 0 (KeV)",
         }]  ,
        'high_threshold1':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"High Energy threshold 1",
             'unit':"KeV",
             'format':"%5.2f",
             'description':"High Energy threshold 1 (KeV)",
         }]  ,
        'low_threshold1':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"Low Energy threshold 1",
             'unit':"KeV",
             'format':"%5.2f",
             'description':"Low Energy threshold 1 (KeV)",
         }] ,
        'dead_time_free_mode':
            [[PyTango.DevString,
            PyTango.SCALAR,
            PyTango.READ_WRITE],
            {
             'label':'Dead Time Free Mode',
             'unit': 'dead_time_free_mode_off/dead_time_free_mode_on',
                }]   ,
        'cooling_temperature_setpoint':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"Setpoint for the peltier cooler.",
             'unit':"C",
             'format':"%5.2f",
             'description':"Cooling temperature setpoint for the peltier module of the detector."
         }]  , 
        'high_voltage_biais':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"High voltage biais.",
             'unit':"V",
             'format':"%5.2f",
             'description':"Biais tension for the high voltage in manual mode."
         }],
        'high_voltage_delay_before_on':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"High voltage delay before on.",
             'unit':"s",
             'format':"%5.2f",
             'description':"Delay for the hv before acquisition.",
         }]  ,
        'h_v_refresh_period':
        [[PyTango.DevShort,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"Refresh period.",
             'unit':"img",
             'description':"How many image before hv is reset.",
         }]  ,
        'delay_between_frames':
        [[PyTango.DevShort,
          PyTango.SCALAR,
          PyTango.READ_WRITE],
         {
             'label':"Waiting time in ms between images.",
             'unit':"ms",
             'description':"delay between frame in loop acquisition.",
         }]  ,
        'color_mode':
            [[PyTango.DevString,
            PyTango.SCALAR,
            PyTango.READ_WRITE],
            {
             'label':'Color mode',
             'unit': 'COLMODE_1COL0, COLMODE_2COL, COLMODE_1COL1, COLMODE_DTF, COLMODE_4COL',
             }],
        'sensor_config_build':
            [[PyTango.DevString,
            PyTango.SCALAR,
            PyTango.READ_WRITE],
            {
             'label':'Config sensor px1 px8 ',
             'unit': 'PX1, PX2, PX8',
             }] ,
        'trsf_mode':
            [[PyTango.DevString,
            PyTango.SCALAR,
            PyTango.READ_WRITE],
            {
             'label':'Moderated or unmoderated udp transport',
             'unit': 'UNMOD, UNMODH, MOD',
             }] ,
        'h_v_bias_mode_power':
            [[PyTango.DevBoolean,
            PyTango.SCALAR,
            PyTango.READ_WRITE],
            {
             'label':'high tension or not',
             }] , 
	    'hybrid_mode':
            [[PyTango.DevString,
            PyTango.SCALAR,
            PyTango.READ_WRITE],
            {
             'label':'substrat type',
             'unit': 'CDTE',
             }] ,
        'temperature_peltier_cold':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Peltier temperature - Cold",
             'unit':"deg C",
             'description':"Temperature of the peltier (live) cold surface.",
         }],
        'temperature_peltier_hot':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Peltier temperature - Hot",
             'unit':"deg C",
             'description':"Temperature of the peltier (live) Hot surface.",
         }],
        'high_voltage_tension':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"High Voltage tension",
             'unit':"V",
             'description':"The tension of the Hihgh Voltage",
         }],
        'box_humidity':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Humidity in the Box",
             'unit':"%",
             'description':"The moisture level in the detector box.",
         }],
        'box_temperature':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Temperature in the Box",
             'unit':"deg C",
             'description':"The temperature in the detector box.",
         }],
        'peltier_power':
        [[PyTango.DevDouble,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Peltier Power",
             'unit':"%",
             'description':"The percentage of peltier power.",
         }],
        'alarm_temp_too_hot':
        [[PyTango.DevBoolean,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Alarm: Temperature is too hot",
             'unit':"%",
             'description':"The temperature is too hot alarm.",
         }],
        'alarm_temp_too_hot_enabled':
        [[PyTango.DevBoolean,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Alarm: <<Temperature is too hot>> survey is Enabled",
             'unit':"%",
             'description':"The Alarm <<Temperature is too hot>> is enabled or not (is watched or not).",
         }],
        'alarm_temp_too_cold':
        [[PyTango.DevBoolean,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Alarm: Temperature is too cold",
             'unit':"%",
             'description':"The temperature is too cold alarm.",
         }],
        'alarm_temp_too_cold_enabled':
        [[PyTango.DevBoolean,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Alarm: <<Temperature is too cold>> survey is Enabled",
             'unit':"%",
             'description':"The Alarm <<Temperature is too cold>> is enabled or not (is watched or not).",
         }],
        'alarm_humidity':
        [[PyTango.DevBoolean,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Alarm: Humidity",
             'unit':"%",
             'description':"The humidity is too high.",
         }],
        'alarm_humidity_enabled':
        [[PyTango.DevBoolean,
          PyTango.SCALAR,
          PyTango.READ],
         {
             'label':"Alarm: Humidity survey is Enabled",
             'unit':"%",
             'description':"The Alarm <<Humidity>> is enabled or not (is watched or not).",
         }]	 
        }


    def __init__(self,name) :
        PyTango.DeviceClass.__init__(self,name)
        self.set_type(name)


#----------------------------------------------------------------------------
#                              Plugins
#----------------------------------------------------------------------------
from Lima import Pixirad as PixiradModule

_PixiradCamera = None
_PixiradInterface = None

def get_control(ip_address = '192.168.0.1',port_number='6666', initial_model = 'PX8', **keys) :
    #properties are passed here as string
    global _PixiradCamera
    global _PixiradInterface


    if _PixiradCamera is None:
        _PixiradCamera = PixiradModule.Camera(ip_address, int(port_number), initial_model)
        _PixiradInterface = PixiradModule.Interface(_PixiradCamera)
        
    return Core.CtControl(_PixiradInterface)

    
def get_tango_specific_class_n_device():
    return PixiradClass,Pixirad
