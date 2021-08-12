RoiCollection
==============

The Roi collection plugin can be used to do data reduction on the image by providing a large number of Roi. The result will a spectrum of data.
The spectrum (command **readSpectrum**) is containing the ROI integration value of the pixels.

In addition to the statistics calculation you can provide a mask file (**setMask** command or **MaskFile** property/attribute) 
where null pixel will not be taken into account.

If you have a detector with pixels which randomly return wrong high count rate, you can use the **OverflowThreshold**
attribute to cut off those defective pixels.

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
OverflowThreshold	rw	DevLong	      cut off pixels above the threshold value
MaskFile                rw      DevString     The mask file
RunLevel		rw	DevLong	      Run level in the processing chain, from 0 to N		
State		 	ro 	State	      OFF or ON (stopped or started)
Status		 	ro	DevString     "OFF" "ON" (stopped or started)
======================= ======= ============= ======================================================================

Commands
--------

=======================	============================ ============================= ==================================================
Command name		Arg. in		             Arg. out		 	   Description
=======================	============================ ============================= ==================================================
clearAllRois		DevVoid	    	     	     DevVoid			   Remove the Rois 
Init			DevVoid		     	     DevVoid			   Do not use
readSpectrum		DevLong 	     	     DevVarLongArray		   from which frame id return the spectrums
                        (number of spectrum,spectrum size, first frame id, spectrum0, spectrum1...)
setMaskFile		DevVarStringArray	     DevVoid			   Set the mask file
			full path file
setRois			DevArLongArray		     DevVoid			   Set roi positions
			(x0,y0,w0,h0,x1,y1,w1,h1 ...)
Start			DevVoid			     DevVoid			   Start the operation on image
State			DevVoid		     	     DevLong		    	   Return the device state
Status			DevVoid		     	     DevString			   Return the device state as a string
Stop			DevVoid		     	     DevVoid			   Stop the operation on image
=======================	============================ ============================= ==================================================
