Roi2Spectrum
=============
The Region-of-Interest to Spectrum operation is very useful to provide online integration of some areas of your detector.
The integration of the pixel values can set along the Y direction or the X direction.
You must create first the Rois by providing unique names (**addNames** command) and then set the Roi position using the index and the x,y, width, height 
(**setRois** command). The direction for integration (so-called mode) can be set using te **setRoiModes** command.
Once the configuration is ok you can start the task using **Start** command and stop the task calling the **Stop** command.
The spectrum data can be retrieved by calling the **readImage** command, the command returns the spectrums as a stack stored into an image.

In addition to the statistics calculation you can provide a mask file (**setMask** command or **MaskFile** property/attribute) 
where null pixel will not be taken into account.

Properties
----------
========================== =============== ====================== =====================================================
Property name		   Mandatory       Default value          Description
========================== =============== ====================== =====================================================
BufferSize                  No              128                   Circular buffer size in image
MaskFile                    No              ""                    A mask file
========================== =============== ====================== =====================================================

Attributes
----------

======================= ======= ============= ======================================================================
Attribute name		RW	Type			Description
======================= ======= ============= ======================================================================
BufferSize		rw	DevLong	      Circular buffer size in image, default is 128
CounterStatus		ro	DevLong	      Counter related to the current number of proceeded images
MaskFile                rw      DevString     The mask file
RunLevel		rw	DevLong	      Run level in the processing chain, from 0 to N		
State		 	ro 	State	      OFF or ON (stopped or started)
Status		 	ro	DevString     "OFF" "ON" (stopped or started)
======================= ======= ============= ======================================================================

Commands
--------

=======================	==================== ============================= ==================================================
Command name		Arg. in		     Arg. out		 	   Description
=======================	==================== ============================= ==================================================
addNames		DevVarStringArray    DevVarStringArray	 	   Set the names and return the corresponding indexes		
			list of Roi names    list of Roi indexes	
clearAllRois		DevVoid	    	     DevVoid			   Remove the Rois 
getNames		DevVoid		     DevVarStringArray	 	   Return the list of Roi names
getRoiModes		DevVarStringArray    DevVarStringArray	 	   Return the Roi modes 
getRois			DevVarStringArray    DevVarStringArray	 	   Return the Roi positions
			list of Roi names    list of Roi position
			     	    	     (roi_id,x,y,width,heigth,...)
Init			DevVoid		     DevVoid			   Do not use
readImage		DevVarLongArray	     DevVarLongArray		 
removeRois		roi_id,first image   spectrum stack		   Return the stack of spectrum from the specified 
				     	   	    			   image index until the last image acquired
setRois			DevArLongArray       DevVoid			   Set roi positions
			(roi_id,x,y,w,h,...)
Start			DevVoid		     DevVoid			   Start the operation on image
State			DevVoid		     DevLong		    	   Return the device state
Status			DevVoid		     DevString			   Return the device state as a string
Stop			DevVoid		     DevVoid			   Stop the operation on image
=======================	==================== ============================= ==================================================
