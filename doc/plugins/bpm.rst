Bpm
=======================

This is the BPM (Beam Position Monitoring) device. It aims to detect an X-ray beam spot and returns statistics (x,y positions, FWHM, ...).
It takes images and calculates the beam position using the builtin task BPM of the processlib library.
It can also push Tango event containing jpeg view of the image and several statistics and information (listed bellow) in a DevEncoded attribute name bvdata.


Properties
----------

====================    ====== ====================  ================================================================================================================
Propertie name          RW     Type                  Description
====================    ====== ====================  ================================================================================================================
enable_bpm_calc         RW     DevBoolean            Enable or disable the bpm calculation algorithm.
enable_tango_event      RW     DevBoolean            if set to false, Bpm won't push bvdata or other attributes through Tango.
calibration             RW     DevVarDoubleArray     Contains the calibration in X and Y ([X,Y]), value in unit/pixel.                                                                  |
beammark                RW     DevVarLongArray       Contains coordinates (X,Y) in pixels of a beam mark set by the user.
====================    ====== ====================  ================================================================================================================


Attributes
----------

====================   ====== ==========      ================================================================================================================
Attribute name         RW     Type            Description
====================   ====== ==========      ================================================================================================================
buffersize             RW     DevLong         Size of the buffer where a certain amount of images will be store before re-writing on the first one.
x                      RO     DevDouble       coordinate on the x axis of the beam return by the BPM task. If the algorithm couldn't find a X value then it
                                              is set at -1.
y                      RO     DevDouble       Same as x but for Y axis.
txy                    RO     DevDouble       Return an array [timestamp,x,y] of the last acquisition.
automatic_aoi          RW     DevBoolean      true or false for the AOI mode.
intensity              RO     DevDouble       Intensity of the area around beam.
max_intensity          RO     DevDouble       Maximum intensity on the image.
proj_x                 RO     DevLong         Array containing sum of all pixel´s intensity on axis x
proj_y                 RO     DevLong         Same as proj_x but on y axis.
fwhm_x                 RO     DevDouble       Full width at half of maximum on the profil X.
fwhm_y                 RO     DevDouble       same as fwhm_x but on y axis profil.
autoscale              RW     DevBoolean      Activate autoscale transformation on the image. (use min and max intensity on it in order to scale).
lut_method             RW     DevString       Method used in the transformation of image. can be "LOG" or "LINEAR".
color_map              RW     DevBoolean      Image in black and white(color_map=false), or use a color map to display colors based on intensity.
bvdata                 RO     DevEncoded      Attribute regrouping the image (jpeg format) and numerous information on it, such as timestamp,
                                              number of the frame, x, y, txy, ...
                                              Everything is pack throught struck module and is either send in a Tango event or directly read.
                                              WARNING : You need to have the decode function in order to read (can be found in the webserver
                                              Bpm, currently here : https://gitlab.esrf.fr/limagroup/bpm-web )
calibration            RW     DevDouble       Attribute version of the calibration property.
beammark               RW     DevLong         Attribute version of the beammark property.
enable_bpm_calc        RW     DevBoolean      Enable or disable the bpm calculation algorithm.
====================   ====== ==========     ================================================================================================================


Commands
----------

====================    ==================== ====================     ================================================================================================================
Commands name		    Arg.IN               Arg.OUT			      Description
====================    ==================== ====================     ================================================================================================================
Start                   DevVoid              DevVoid                  Start Bpm device.
Stop                    DevVoid              DevVoid                  Stop Bpm device.
getResults              DevLong              DevVarDoubleArray        Take a number as parameter and return an array containing (framenb,x,y) values, starting to the
                                                                      frame number ask until there is no more image.
GetPixelIntensity       DevVarLongArray      DevLong                  Return the intensity of pixel (x,y) passed as parameters
HasBackground           DevVoid              DevBoolean               Is there a background already in place ?
TakeBackground          DevVoid              DevVoid                  Take the current image and set it as Background, using the Core.BACKGROUNDSUBSTRACTION module.
ResetBackground         DevVoid              DevVoid                  Reset the Background.
====================    ==================== ====================     ================================================================================================================

NOTE
----------
This plugin is supposed to replace the old BeamViewer plugin but with limited functionalities for the moment.
Some other plugins will be created in the future.
This plugin is mainly used in conjunction with the `bpm webserver application <https://gitlab.esrf.fr/limagroup/bpm-web>`_
