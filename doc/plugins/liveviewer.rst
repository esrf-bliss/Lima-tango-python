LiveViewer
===========

This device was create for backward compatibility with former graphical applications used at ESRF by the diagnostic group for the monitoring
of the electron beam. It is no longer maintained. Instead we recommend to use the video API provided via the main device LimaCCDs.

Nevertheless you will find here the of the available properties, attributes and commands.

Properties
----------

======================= =============== =============== ================================================
Property name	        Mandatory	Default value	Description
======================= =============== =============== ================================================
AcquisitionAutoStart	No		False           If true start the acquistion at device startup
======================= =============== =============== ================================================


Attributes
----------

======================= ======= =================== ======================================================================
Attribute name		rw	Type			Description
======================= ======= =================== ======================================================================
Depth			ro	DevShort	    Image depth in byte
Exposure		rw	DevDouble	    Exposure time in second
ExternalTrigger		rw	DevBoolean	    External trigger active if true
FrameRate		rw	DevDouble	    Frame rate in fps
Frames			rw	DevLong		    Number of frames to acquire
Gain			rw	DevDouble	    Gain, support depends on the camera model
Image			ro	Image, DevUShort    The last image taken
ImageCounter		ro	DevLong		    The image counter
JpegImage		ro	DevEncoded	    The last image in JPEG format, only supported for B/W cameras.
JpegQuality		rw	DevLong		    JPEG quality factor from 0 to 10
Roi			rw	DevLong,Spectrum    The Roi position, start x, start y, width, height
State		 	ro 	State	      	    OFF or ON (stopped or started)
Status		 	ro	DevString     	    "OFF" "ON" (stopped or started)
======================= ======= =================== ======================================================================

Commands
--------

=======================	=============== =======================	===========================================
Command name		Arg. in		Arg. out		Description
=======================	=============== =======================	===========================================
Init			DevVoid 	DevVoid			Do not use
Reset			DevVoid		DevVoid			Reset the camera, factory setting is apply
ResetRoi		DevVoid		DevVoid			Remove the Roi, camera set to full size
Start			DevVoid		DevVoid			Start the camera for live acquisition
State			DevVoid		DevLong			Return the device state
Status			DevVoid		DevString		Return the device state as a string
Stop			DevVoid		DevVoid			Stop the camera live
=======================	=============== =======================	===========================================


