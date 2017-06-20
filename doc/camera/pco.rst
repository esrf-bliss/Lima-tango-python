PCO Tango device
================

This is the reference documentation of the PCO Tango device.

you can also find some useful information about the camera models/prerequisite/installation/configuration/compilation in the :ref:`PCO camera plugin <camera-pco>` section.


Properties
----------

=============== =============== =============== ==============================================================
Property name   Mandatory       Default value   Description
=============== =============== =============== ==============================================================
debug_control   No              0               Enable/Disble the debug (0/1)
debug_module    No              0               To set the debug module list (in hex format 0x....)
                                                 - None           = 0x001
                                                 - Common         = 0x002
                                                 - Hardware       = 0x004
                                                 - HardwareSerial = 0x008
                                                 - Control        = 0x010
                                                 - Espia          = 0x020
                                                 - EspiaSerial    = 0x040
                                                 - Focla          = 0x080
                                                 - Camera         = 0x100
                                                 - CameraCom      = 0x200
                                                 - Test           = 0x400
                                                 - Application    = 0x800
debug_format    No              0               To set the debug format (in hex format 0x....)
                                                 - DateTime = 0x001
                                                 - Thread   = 0x002
                                                 - Module   = 0x004
                                                 - Obj      = 0x008
                                                 - Funct    = 0x010
                                                 - FileLine = 0x020
                                                 - Type     = 0x040
                                                 - Indent   = 0x080
                                                 - Color    = 0x100
debug_type      No              0               To set the debug type (in hex format 0x....)
                                                 - Fatal   = 0x001
                                                 - Error   = 0x002
                                                 - Warning = 0x004
                                                 - Trace   = 0x008
                                                 - Funct   = 0x010
                                                 - Param   = 0x020
                                                 - Return  = 0x040
                                                 - Always  = 0x080
params          No              empty            List of parameters/options (one per line)
                                                  - trigSingleMulti = 1 
                                                    (enable TriggerSingleMulti as TriggerMulti for compability
                                                    with SPEC START)  
                                                  - xMinSize = 1
                                                    (enable correction for the X minimum size for the CLHS firmware bug) 
=============== =============== =============== ==============================================================


Attributes
----------

======================= ======= ======================= ======================================================================
Attribute name          RW      Type                    Description
======================= ======= ======================= ======================================================================
acqTimeoutRetry         rw      DevLong                 Maximum Timeout retries during acq (0 - infinite)
adc                     rw      DevLong                 Number of working ADC's
adcMax                  ro      DevLong                 Maximum number of ADC's
binInfo                 ro      DevLong                 PCO hw binning info
bytesPerPixel           ro      DevLong                 Bytes per Pixel
camInfo                 ro      DevString               General camera parameters information
camName                 ro      DevString               Camera Name
camNameBase             ro      DevString               Camera Name (Pco)
camNameEx               ro      DevString               Camera Name, Interface, Sensor
camType                 ro      DevString               Camera Type
cdiMode                 rw      DevLong                 Correlated Double Imaging Mode
                                                         - enabled/disabled = 1/0 (rw)
                                                         - not allowed = -1 (ro)
clXferPar               ro      DevString               General CameraLink parameters
cocRunTime              ro      DevDouble               cocRunTime (s) - only valid after the camera is armed
coolingTemperature      ro      DevDouble               Cooling Temperature
firmwareInfo            ro      DevString               Firmware info
frameRate               ro      DevDouble               Framerate, calculated as: 1/cocRunTime (1/s)
info                    ro      DevString               General camera parameters information
lastError               ro      DevString               The last PCO error message
lastImgAcquired         ro      DevLong                 Last image acquired (during recording)
lastImgRecorded         ro      DevLong                 Last image recorded (during recording)
logMsg                  ro      DevString               Last Log msgs
logPcoEnabled           ro      DevLong                 PCO logs are enabled
maxNbImages             ro      DevLong                 The maximum number of images which can be acquired by the camera (recording mode)
pixelRate               ro      DevLong                 Actual Pixel Rate (Hz)
pixelRateInfo           ro      DevString               Pixel Rate information
pixelRateValidValues    ro      DevString               Allowed Pixel Rates
roiInfo                 ro      DevString               PCO ROI info
roiLastFixed            ro      DevString               Last fixed ROI info
rollingShutter          rw      DevLong                 Rolling Shutter Mode (**only for some types of EDGE**)
                                                         - 1 = ROLLING
                                                         - 2 = GLOBAL
                                                         - 4 = GLOBAL RESET
rollingShutterInfo      ro      DevString               Rolling Shutter info
temperatureInfo         ro      DevString               Temperature info
traceAcq                ro      DevString               Debug information for some types of acq
version                 ro      DevString               Version information of the plugin
versionAtt              ro      DevString               Version of att file
versionSdk              ro      DevString               PCO SDK Release
======================= ======= ======================= ======================================================================

For the above attributes which use "talk" command you can refer to the PCO documentation for more information.

Commands
--------

======================= =============== ======================= ===========================================
Command name            Arg. in         Arg. out                Description
======================= =============== ======================= ===========================================
Init                    DevVoid         DevVoid                 Do NOT use
State                   DevVoid         DevLong                 Return the device state
Status                  DevVoid         DevString               Return the device state as a string
getAttrStringValueList  DevString:      DevVarStringArray:      Return the authorized string value list for
                        Attribute name  String value list       a given attribute name
talk                    DevString       DevString               **WARNING**: use this command for test only, 
                                                                This is a backdoor cmd and it can distrub Lima
======================= =============== ======================= ===========================================
