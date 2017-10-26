Python TANGO server
====================

This is the python Tango devices server by the ESRF team.

This server provides a main device for the standard camera control, a camera specific device for the camera configuration and a set of "plugin" devices for extra operations or just to provide some specific API for clients.

Thanks to the Lima framework,  the control can be achieved through a common server and a set of software operations (Mask,Flatfield,Background,RoiCounter,PeakFinder...) on image as well. The configuration of the detector is done by  the specific detector device. 
At ESRF we decided to develop the Tango devices only in python language which implies that all the detector C++ interfaces have been wrapped in python.

Main device: LimaCCDs
----------------------

**LimaCCDs** is the generic device and it provides a unique interface to control any supported cameras. One can find below the 
commands, the attributes and the properties. 

To run a LimaCCDs server you will need at least to configure the **LimaCameraType** property. This property is used by  the LimaCCDs server to create
the proper camera device. Pleas refer a specific camera (e.g Basler) device chapter for further information.

Property
''''''''
========================== =============== ====================== =====================================================
Property name		   Mandatory       Default value          Description
========================== =============== ====================== =====================================================
AccThresholdCallbackModule No              ""                     Plugin file name which manages threshold, see acc_saturated\_\* attributes and the \*AccSaturated\* commands to activate and use  this feature
BufferMaxMemory		   No		   70			  The maximum among of memory in percent of the available RAM
			   		   			  that Lima is using to allocate frame buffer.
ConfigurationFilePath      No              ~/lima_<serv-name>.cfg The default configuration file path
ConfigurationDefaultName   No              "default"              Your default configuration name
IntrumentName		   No		   ""			  The instrument name, e.g ESRF-ID02 (**\***)
LimaCameraType		   Yes             N/A                    The camera type: e.g. Maxipix
MaxVideoFPS		   No		   30			  Maximum value for frame-per-second
NbProcessingThread         No              1                      The max number of thread for processing.
                                                                  Can be used to improve the performance 
                                                                  when more than 1 task (plugin device) is activated
TangoEvent		   No              False		  Activate Tango Event for counters and new images
UserDetectorName	   No		   ""			  A user detector identifier, e.g frelon-saxs, (**\***)
========================== =============== ====================== =====================================================

(**\***) Properties only used to set meta-data in HDF5 saving format.


Commands
'''''''''
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|**Command name**            |**Arg. in**                                |**Arg. out**                         |**Description**                                                                                      |
+============================+===========================================+=====================================+=====================================================================================================+
|Init                        |DevVoid                                    |DevVoid                              |Do not use                                                                                           |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|State                       |DevVoid                                    |DevLong                              |Return the device state                                                                              |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|Status                      |DevVoid                                    |DevString                            |Return the device state as a string                                                                  |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|getAttrStringValueList      |DevString:			         |DevVarStringArray:		       |		                                                                                     |
|			     |Attribute name		                 |String value list		       |Return the authorized string value list for a given attribute name                                   |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|prepareAcq                  |DevVoid                                    |DevVoid                              |Prepare the camera for a new acquisition, has to be called each time a parameter is set.             |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|startAcq                    |DevVoid                                    |DevVoid                              |Start the acquisition                                                                                |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|stopAcq                     |DevVoid                                    |DevVoid                              |Stop the acquisition after current frame is acquired, and wait for all tasks to finish               |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|abortAcq                    |DevVoid                                    |DevVoid                              |Abort the acquisition, the current frame is lost                                                     |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|setImageHeader              |DevVarStringArray:                         |				       |	                                                                                             |
|                            |Array of string header                     |DevVoid                              |Set the image header:                                                                                |
|			     |   	                                 |                                     | - [0]="ImageId0 delimiter imageHeader0,                                                             |
|		     	     |					         |     				       | - [1] = ImageId1 delimiter  imageHeader1..                                                          |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|resetCommonHeader           |DevVoid                                    |DevVoid                              |Reset the common header                                                                              |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|resetFrameHeaders           |DevVoid                                    |DevVoid                              |Reset the frame headers                                                                              |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|getImage                    |DevLong: Image number(0-N)                 |DevVarCharArray: Image data          |Return the image data in raw format (char array)                                                     |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|getBaseImage                |DevLong: Image number(0-N)                 |DevVarCharArray: Image data          |Return the base image data in raw format (char array). Base image is the raw image before processing |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|readImage                   |DevLong: Image number(0-N)                 |DevEncoded: Encoded image            |Return the image in encoded format of type "**DATA_ARRAY**" (see :ref:`data_array_encoded`)          |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|readImageSeq                |DevLongArray: Image number(0-N) list       |DevEncoded: Encoded image(S)         |Return a stack of images in encoded format of type "**DATA_ARRAY**" (see :ref:`data_array_encoded`)  |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|writeImage                  |DevLong: Image number(0-N)                 |DevVoid                              |Save manually an image                                                                               |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|readAccSaturatedImageCounter|DevLong: Image number                      |DevVarUShortArray: Image counter     |The image counter                                                                                    |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|readAccSaturatedSumCounter  |DevLong: from image id                     |DevVarLongArray: result              |number of result for each images,sum counter of raw image #0 of image #0,sum counter of raw image #1 |
|                            |                                           |                                     |of image #0,...                                                                                      |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|setAccSaturatedMask         |DevString                                  |DevVoid                              |Full path of mask file, use empty string ("") to unset the mask                                      |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|closeShutterManual          |DevVoid                                    |DevVoid                              |Only if the camera has this capability                                                               |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|openShutterManual           |DevVoid                                    |DevVoid                              |Only if the camera has this capability                                                               |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|reset                       |DevVoid                                    |DevVoid                              |Reset the camera to factory setting                                                                  |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|getPluginDeviceNameFromType |DevString                                  |DevString                            |Return the device name corresponding to the passed plugin named (.e.g FlatField)                     |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|configStore                 |DevVarStringArray:config name,module1,     |DevVoid                              |Store (im memory) a current config with name and for the listed modules (e.g. **Acquisition**,       |
|                            |module2, ... , modulen                     |                                     |**Image**, **RoiCounters**, **Saving** ...).                                                         |
|                            |                                           |                                     |See the *config_available_name* and *config_available_module* attributes for full list.              | 
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|configApply                 |DevString: config name                     |DevVoid                              |Apply the named config                                                                               |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|configPop                   |DevVoid                                    |DevVoid                              |Pop the named config from the list                                                                   |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|configDelete                |DevVoid                                    |DevVoid                              |Delete the named config                                                                              |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|configFileSave              |DevVoid                                    |DevVoid                              |Save all the config into file (see properties for config file name)                                  |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+
|configFileLoad              |DevVoid                                    |DevVoid                              |Load the configs from file                                                                           |
+----------------------------+-------------------------------------------+-------------------------------------+-----------------------------------------------------------------------------------------------------+


Attributes
''''''''''

You will here a long list of attributes, this reflects the richness of the LIMA library. We organized them in
modules which correspond to specific functions. A function module is identified by an attribute name prefix (excepted for informationnal attributes),
for instance the **Acquisition** module attributes  are always named **acq_<attr-name>**. The available modules are :

 * General Information 
 * Status  (prefix *last_* and *ready_*)
 * Acquisition (prefix *acq_* for most of them sorry)
 * Accumulation (prefix *acc_*)
 * Saving  (prefix *saving_*)
 * Image (prefix *image_*)
 * Shutter (prefix *shutter_*)
 * Debug   (prefix *debug_*)
 * Video   (prefix *video_*)
 * Shared Memory (prefix *shared_memory_*)
 * Configuration (prefix *config_*)
 * Buffer (prefix *buffer_*)
 * Plugin (prefix *plugin_*) 

Many attributes are of type DevString and they have a fixed list of possible values. you can get the list by calling the special command
**getAttrStringValueList**. Because a camera cannot support some attribute values , the command getAttrStringValueList will give you the 
the value list for the camera. For instance the attribute *video_mode* supports up to 14 different video formats, but a camera can only supports
few of them.


=========================== ======= ======================= =======================================================================================
Attribute name		    RW	    Type		    Description
=========================== ======= ======================= =======================================================================================
\                           \       **GENERAL INFORMATION** \
lima_type		    ro	    DevString		    LImA camera type: 
							    Maxipix,Pilatus,Frelon,Pco, Basler ...
camera_type                 ro      DevString		    Like lima_type but in upper-case  !!
camera_pixelsize            ro      DevDouble[x,y]          The camera pixel size in x and y dimension
camera_model		    ro	    DevString		    Camera model return by the detector layer:.e.g. 5x1- TPX1
\                           \       \                       \
\                           \       **STATUS**              \
last_base_image_ready       ro      DevLong                 The last base (before treatment) ready 
last_image_ready	    ro	    DevLong		    The last acquired image number, ready for reading
last_image_saved	    ro	    DevLong		    The last saved image number
last_image_acquired         ro      DevLong                 The last acquired image number
last_counter_ready          ro      DevLong                 Tell which image counter is last ready
ready_for_next_image	    ro	    DevBoolean		    True after a camera readout, otherwise false. Can be
							    used for fast synchronisation with trigger mode (internal
							    or external).
ready_for_next_acq	    ro	    DevBoolean		    True after end of acquisition, otherwise false.
user_detector_name	    rw	    DevString		    User detector name
instrument_name		    rw	    DevString		    Intrument/beamline name
\                           \       \                       \
\                           \       **ACQUISITION**         \
acq_status		    ro	    DevString		    Acquisition status: Ready, Running, Fault or Configuration
acq_status_fault_error	    ro	    DevString		    In case of Fault state, return the error message
acq_mode		    rw	    DevString		    Acquisition mode:
							     - **Single**, default mode one frame per image
							     - **Concatenation**, frames are concatenated in image
							     - **Accumulation**, powerful mode to avoid saturation 
							       of the pixel, the exposure is shared
							       by multiple frames, see acc\_ attributes for more

acq_nb_frames		    rw	    DevLong	            Number of frames to be acquired, Default is 1 frame
acq_trigger_mode	    rw	    DevString		    Trigger mode:
							     - **Internal_trigger**, the software trigger, 
							       start the acquisition immediately after an acqStart() call,
							       all the acq_nb_frames are acquired in an sequence.
							     - **External_trigger**, wait for an external trigger signal 
							       to start the an acquisition for the acq_nb_frames number 
							       of frames.
							     - **External_trigger_multi**, as the previous mode except 
							       that each frames need a new trigger input 
							       (e.g. for 4 frames 4 pulses are waiting for)
							     - **Internal_trigger_multi**, as for internal_trigger except 
							       that for each frame the startAcq() has to called once.
							     - **External_gate**, wait for a gate signal for each frame, 
							       the gate period is the exposure time.
							     - **External_start_stop**

latency_time		    rw	    DevDouble		    Latency time in second between two frame acquisitions,
							    can not be zero, the minimum time corresponds to the
							    readout time of the detector.
valid_ranges                ro      DevDouble[4]            min exposure, max exposure, min latency, max latency
concat_nb_frames            rw      DevLong                 The nb of frames to concatenate in one image
acq_expo_time		    rw	    DevDouble		    The exposure time of the image, Default is 1 second
\                           \       \                       \
\                           \       **ACCUMULATION**        \
acc_expotime		    ro	    DevDouble		    The effective accumulation total exposure time.
acc_nb_frames		    ro	    DevLong		    The calculated accumulation number of frames per image.
acc_max_expotime	    rw	    DevDouble		    The maximum exposure time per frame for accumulation
acc_time_mode		    rw	    DevString		    Accumulation time mode:
							     - **Live**,acq_expo_time = acc_live_time
							     - **Real**,acq_expo_time = acc_dead_time + acc_live_time

acc_dead_time		    ro	    DevDouble		    Total accumulation dead time
acc_live_time		    ro	    DevDouble		    Total accumulation live time which corresponds to the
							    detector total counting time.
acc_offset_before           rw      DevLong                 Set a offset value to be added to each pixel value
acc_saturated_active        rw      DevBoolean              To activate the saturation counters (i.e. readAccSaturated commands)
acc_saturated_cblevel       rw      DevLong                 Set at which level of total saturated pixels the callback plugin (if set with the AccThresholdCallbackModule property) will be called
acc_saturated_threshold     rw      DevLong                 The threshold for counting saturated pixels
acc_threshold_before        rw      DevLong                 Set a threshold value to be substract to each pixel value
\                           \       \                       \
\                           \       **SAVING**              \
saving_mode		    rw	    DevString		    Saving mode:
							     - **Manual**, no automatic saving, a command will
							       be implemented in a next release to be able to
							       save an acquired image.
							     - **Auto_Frame**, Frames are automatically saved
							       according the saving parameters (see below).
							     - **Auto_header**, Frames are only saved when the
							       setImageHeader() is called in order to set
							       header information with image data.

saving_directory	    rw	    DevString		    The directory where to save the image files
saving_prefix		    rw	    DevString		    The image file prefix
saving_suffix		    rw	    DevString		    The image file suffix
saving_next_number	    rw	    DevLong		    The image next number
							    The full image file name is:
							    /saving_directory/saving_prefix+sprintf("%04d",saving_next_number)+saving_suffix
saving_format		    rw	    DevString		    The data format for saving:
							     - **Raw**, save in binary format
							     - **Edf**, save in ESRF Data Format
							     - **edfgz** (or edf.gz), EDF with gz compression
							     - **Tiff**, The famous TIFF format
							     - **Cbf**, save in CBF format (a compressed format
							       for crystallography)

saving_overwrite_policy	    rw	    DevString		    In case of existing files an overwite policy is mandatory:
							     - **Abort**, if the file exists the saving is aborted
							     - **Overwrite**, if the file exists it is overwritten
							     - **Append**, if the file exists the image is append
							       to the file 

saving_frame_per_file	    rw	    DevLong		    Number of frames saved in each file
saving_common_header	    rw	    DevString[]		    Common header with multiple entries
saving_header_delimiter     rw	    DevString[]		    The header delimiters, [0] = key header delimiter, [1] =
				                            entry header delimiter, [2] = image number header
							    delimiter. Default : [0] = "=", [1] = "\n", [2] = ";"
saving_max_writing_task     rw      DevShort                Set the max. tasks for saving file, default is 1
saving_statistics           ro	    DevDouble[]		    Return stats: saving speed, compression ratio,
                                                            compression speed and incoming speed (speed in byte/s)
saving_statistics_history   rw	    DevLong		    Set size of history for stats calculation, default is 16 frames					 
\                           \       \                       \
\                           \       **IMAGE**               \
image_type		    ro	    DevString		    Return the current image data type, bit per pixel signed or unsigned:
							     - Bpp8, Bpp8S, Bpp10, Bpp10S, Bpp12, Bpp12S, Bpp14,
							     - Bpp14S, Bpp16, Bpp16S, Bpp32, Bpp32S , Bpp32F.
image_width		    ro	    DevLong	            Width size of the detector in pixel
image_height		    ro	    DevLong		    Height size of the detector in pixel
image_sizes                 ro      DevULong[4]             Signed(0-unsigned,1-signed), depth(nb bytes), width and height
image_roi		    rw	    DevLong[4]		    Region Of Interest on image, [0] = Begin X, [1] = End X,
							    [2] Begin Y, [3] = End Y, default ROI is [0,0,0,0] (no ROI)
image_bin		    rw	    DevLong[2]		    Binning on image, [0] = Binning factor on X, [1] =
							    Binning factor on Y. Default binning is 1 x 1
image_flip		    rw	    DevBoolean[2]	    Flip on the image, [0] = flip over X axis, [1] flip over Y
				           		    axis. Default flip is False x False
image_rotation              rw      DevString               Rotate the image: "0", "90", "180" or "270"
\                           \       \                       \
\                           \       **SHUTTER**             \
shutter_mode		    rw	    DevString		    Synchronization for shutter,  modes are available:
							     - **Manual**
							     - **Auto_frame**, the output signal is activated for each individual frame of a sequence
							     - **Auto_sequence**, the output signal is activated
							       during the whole sequence
shutter_open_time	    rw	    DevDouble		    Delay (sec.) between the output shutter trigger and the
							    beginning of the acquisition, if not null the shutter signal
							    is set on before the acquisition is started.
shutter_close_time	    rw	    DevDouble		    Delay (sec.) between the shutter trigger and the end of
							    the acquisition, if not null the shutter signal is set on
							    before the end of the acquisition.
shutter_manual_state        rw      DevString               To open/close manually the shutter (if Manual mode is supported, see shutter_mode)
\                           \       \                       \
\                           \       **DEBUG**               \
debug_module_possible       ro      DevString[]             Return the list of possible debug modules
debug_modules		    rw	    DevString[]		    Set the debug module level of LImA:		
							     - "None"
							     - "Common"
							     - "Hardware"
							     - "HardwareSerial"
							     - "Control"
							     - "Espia"
							     - "EspiaSerial"
							     - "Focla"
							     - "Camera"
							     - "CameraCom"
							     - "Test"
							     - "Application"
debug_types_possible        ro      DevString[]             Return the list of the possible debug types
debug_types		    rw	    DevString[]		    Set the debug type level of LImA: 
							     - "Fatal"
							     - "Error"
							     - "Warning"
							     - "Trace"
							     - "Funct"
							     - "Param"
							     - "Return"
							     - "Always"
\                           \       \                       \
\                           \       **VIDEO**               \
video_active                rw      DevBoolean              Start the video mode (or not)
video_live                  rw      DevBoolean              Start the video streaming (or not)
video_exposure              rw      DevDouble               The video exposure time (can be different to the acq_expo_time)
video_gain                  rw      DevDouble               The video gain (if supported by the hardware)
video_mode                  rw      DevString               The video mode is the video format supported by the camera, it can be:
                                                             - Y8, grey image 8bits
							     - Y16, grey image 16bits
							     - Y32, grey image 32bits
							     - RGB555, color image RGB 555 encoding
							     - RGB564, color image RGB 555 encoding
							     - RGB24,  color image RGB 24bits encoding
							     - RGB32, color image RGB 32bits encoding
							     - BGR24, color image BGR 24bits encoding
							     - BGR32, color image BGR 32bits encoding
							     - BAYER_RG8, color image BAYER RG 8bits encoding
							     - BAYER_RG16, color image BAYER RG 16bits encoding
							     - I420, color image I420 (or YUV420) planar encoding
							     - YUV411, color image YUV411 planar encoding
							     - YUV422PACKED, color image YUV422 planar encoding packed
 							     - YUV422, color image YUV422 planar encoding
							     - YUV444, color image YUV444 planar encoding

							    Depending of your camera, the supported formats can be retrieve
							    using the command **getAttrStringValueList**
video_roi                   rw      DevLong[4]              A ROI on the video image (independent of the image_roi attribute)
video_bin                   rw      DevULong[2]             A Binning on the video image (independt of the image_bin attribute)
video_last_image            rw      DevEncoded              The last video image, in DevEncoded "**VIDEO_IMAGE**" format, and using 
                                                            the video_mode set, see the DevEncoded definition :ref:`video_image_encoded`
video_source                rw      DevString               The source for video image, BASE_IMAGE (raw image) or LAST_IMAGE (after soft operation)
                                                            Only valid with monochrome or scientific cameras							 
                                                         
video_last_image_counter    rw      DevLong64               The image counter
\                           \       \                       \
\                           \       **SHARED MEMORY**       \
shared_memory_names         rw      DevString[2]            Firstname and surname of the SPS typed shared memory (default is LimaCCDs,<camera_type>)                      
shared_memory_active        rw                              Activate or not the shared memory. The shared memory is for image display
\                           \       \                       \
\                           \       **CONFIG**              \
config_available_module     ro      DevString[]             List of possible config modules, 
config_available_name       ro      DevString[]             List of existing config names
\                           \       **BUFFER**              \
buffer_max_memory	    rw	    DevShort		    The maximum among of memory in percent of the available RAM
			   		   		    that Lima is using to allocate frame buffer.
\                           \       **PLUGIN**              \
plugin_type_list	    ro	    DevString[]		    List of the available plugin type, to get one device name
                                                            use instead the **getPluginDeviceNameFromType** command
plugin_list                 ro      DevString[]             List of the available plugin as couple of type, device name
=========================== ======= ======================= =======================================================================================


.. _data_array_encoded:

DevEncoded DATA_ARRAY
``````````````````````

The DATA_ARRAY DevEncoded has been invented for special Tango client like SPEC. It is used by the **readImage** command.
It can only embed raw data (no video data). The supported image format can be retrieve with the **image_type** attribute (Bpp8,Bpp8S, ..., Bpp16,..)
This encoded format is very generic and it supports many different type of data from scalar to image stack (see DataArrayCategory enumerate C-type).
The readImage command only supports  *Image* data array category.

The DATA_ARRAY format is composed of a fixed header followed by the raw data. The header is a C-like structure,
with **little-endian** byte order and no alignment::

  # The DATA_ARRAY definition
  struct {
      unsigned int       magic= 0x44544159; // magic key
      unsigned short     version;           // version, only 1 supported
      unsigned  short    header_size;       // size of the header
      DataArrayCategory  category;          // data array category, see DataArrayCategory enumerate
      DataArrayType      data_type;         // data type, see DataArrayType enumerate
      unsigned short     endianness;        // 0-little-endian, 1-big-endian
      unsigned short     nb_dim;            // number of dimension (0 to 7 max)e.g 2 for image
      unsigned short     dim[8];            // size for each dimension, e.g [width,height]
      unsigned int       dim_step[8];       // step size in pixel for each dimension, e.g [1,height]
  } DATA_ARRAY_STRUCT;

  enum DataArrayCategory {
      ScalarStack = 0;
      Spectrum;
      Image;
      SpectrumStack;
      ImageStack;
  };

  enum DataArrayType{
      DARRAY_UINT8 = 0;
      DARRAY_UINT16;
      DARRAY_UINT32;
      DARRAY_UINT64;
      DARRAY_INT8;
      DARRAY_INT16;
      DARRAY_INT32;
      DARRAY_INT64;
      DARRAY_FLOAT32;
      DARRAY_FLOAT64;
  };

.. _video_image_encoded:

DevEncoded VIDEO_IMAGE
``````````````````````
The VIDEO_IMAGE DevEncoded has been implemented for the **video_last_image** attribute to return the last image. It can
embed any of the supported video format depending of the **video_mode** attribute value.

The VIDEO_IMAGE format is composed of a fixed header followed by the  data. The header is a C-like structure,
with  **big-endian** byte order  and no alignment::

 struct {
     unsigned int     magic_number = 0x5644454f;
     unsigned short   version;        // only version 1 is supported
     unsigned short   image_mode;     // Y8,Y16,....
     long     long    frame_number;   // the frame number (counter)
     int              width;          // the frame width in pixel (horizontal size)
     int              height          // the frame height in pixel (vertical size)
     unsigned short   endianness;     // 0-little-endian, 1-big-endian
     unsigned short   header_size;    // this header size in byte
     unsigned short   padding[2];     // 4 bytes of padding (for alignment)
 } VIDEO_IMAGE_STRUCT;



Camera devices
--------------------
Each camera has a configuration device with its own property/attribute/command lists. 
The camera configuration device is supposed to give you access to the "private" parameters
of the detector that LIMA does not need but you may want to set. For instance some detectors
provides a temperature control with set-points and/or start/stop commands for a auxillary cooling
system.

For more details about the camera device interface, please have a look on the following sections:

.. toctree::
  :maxdepth: 1

  Andor <camera/andor>
  Andor3 <camera/andor3>
  Basler <camera/basler>
  Dexela <camera/dexela>
  Frelon <camera/frelon>
  ImXPAD <camera/imxpad>
  Maxipix <camera/maxipix>
  Merlin <camera/merlin>
  Dectris Eiger <camera/eiger>
  Dectris Mythen3 <camera/mythen3>
  Dectris Pilatus <camera/pilatus>
  PCO <camera/pco>
  Perkin Elmer <camera/perkinelmer>
  Pixirad <camera/pixirad>
  Photonic Science <camera/photonicscience>
  PointGrey <camera/pointgrey>
  Prosilica <camera/prosilica>
  Rayonix HS <camera/rayonixhs>
  Roper Scientific <camera/roperscientific>
  Simulator <camera/simulator>
  SlsDetector <camera/slsdetector>
  Ueye <camera/ueye>
  Ultra <camera/ultra>
  V4l2 <camera/v4l2>
  XH <camera/xh>
  Xpad <camera/xpad>
  Xspress3 <camera/xspress3>


Plugin devices: software operation and extra interfaces
-------------------------------------------------------

User-defined software plugins can be used to execute arbitrary image-based operations. An entry point in the control layer completely exports the ProcessLib functionality, allowing an external code to be called on every frame. The software operation can be implemented in C++ or Python.

The software operations on image are embedded into individual Tango devices and are available in the **plugins/** directory. They are automatically exported
by the LimaCCDs server. 

The software operations are of two types, *Sink* or *Link* : 
 * **Link** operation is supposed to modify the frame data, so it gets the frame data as input parameter and it will return a "corrected" image (e.g. Mask/Flatfield/BackgroundSubstraction).
 * **Sink** operation  is taken the frame data as input parameter to apply some software operation in order to return new data like statistics, peak positions, alarm on saturation ... etc.

In addition to sink/link plugin device, a plugin can just be implemented to provide/export a subset of the Lima interface or a legacy interface for some specific client applications (e.g SPEC, LimaTacoCCD plugin).



Today there are about  8 standard plugin devices:

* BackgroundSubstraction : link operation, to correct the frames with a background image (substraction)
* FlatField:               link operation to correct the frames with a flatfield image (divide + option normalisation)
* Mask:                    link operation to mask pixels. Very useful if some pixel are not working properly and if you want to set then to a fix value or to zero.
* PeakFinder:              thanks to Teresa Numez from DESY, a sink operation which can detect diffraction peaks.
* Roi2Spectrum:            sink operation to apply ROI spectrum on the frames. You can define more than one spectra with ROI coordinates and by specifying in which direction you need to bin the values, vertical or horizontal.
* RoiCounter:              sink operation to get calculating statistics on image regions. 


* LimaTacoCCD: extra interface for TACO clients, it only provides commands (TACO does not have attribute !), it is still used at ESRF for SPEC.
* LiveViewer:  extra interface  to provide a live view of the last acquired image, can be used from atkpanel.

If you need to implement your own plugin device we can provide you some example codes, use the mailing-list lima@esrf.fr to get help.


.. toctree::
  :maxdepth: 1

  plugins/backgroundsubstraction
  plugins/flatfield
  plugins/mask
  plugins/peakfinder
  plugins/roi2spectrum
  plugins/roicounter
  plugins/limatacoccd
  plugins/liveviewer
