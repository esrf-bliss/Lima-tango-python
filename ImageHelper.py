############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2017
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
import numpy
import struct
from Lima import Core
#============================================================================
#                              HELPERS  
#============================================================================
#
# Here is some helper to marshal data images to Tango data
# DATA_ARRAY DevEncoded 
#enum DataArrayCategory {
    #ScalarStack = 0;
    #Spectrum;
    #Image;
    #SpectrumStack;
    #ImageStack;
#};

class DataArrayCategory:
    ScalarStack, Spectrum, Image, SpectrumStack, ImageStack = range(5)

#enum DataArrayType{
  #DARRAY_UINT8 = 0;
  #DARRAY_UINT16;
  #DARRAY_UINT32;
  #DARRAY_UINT64;
  #DARRAY_INT8;
  #DARRAY_INT16;
  #DARRAY_INT32;
  #DARRAY_INT64;
  #DARRAY_FLOAT32;
  #DARRAY_FLOAT64;
#};

DataType2DataArrayType = {
    numpy.uint8 : 0,
    numpy.uint16 : 1,
    numpy.uint32 : 2,
    numpy.int8 : 4,
    numpy.int16 : 5,
    numpy.int32 : 6,
    numpy.float32 : 8,
    }        

# The DATA_ARRAY definition
#struct {
  #unsigned int Magic= 0x44544159;
  #unsigned short Version;
  #unsigned  short HeaderLength;
  #DataArrayCategory Category;
  #DataArrayType DataType;
  #unsigned short DataEndianness;
  #unsigned short NbDim;
  #unsigned short Dim[8]
  #unsigned int DimStep[8]
#} DataArrayHeaderStruct;

DataArrayVersion = 2
DataArrayPackStr = '<IHHIIHHHHHHHHIIIIIIII'
DataArrayMagic = struct.unpack('>I', 'DTAY')[0]	# 0x44544159
DataArrayHeaderLen = 64
DataArrayMaxNbDim = 6

def DataArrayUser(klass, DataArrayCategory=DataArrayCategory):
    klass.DataArrayCategory = DataArrayCategory
    return klass

##@brief get a DATA_ARRAY from a Data object
#
def image_2_data_array(data, category = DataArrayCategory.Image,
                       force_release_data = False):
    d = data.buffer
    s = [d.shape[i] for i in xrange(len(d.shape) - 1, -1, -1)]
    if (category == DataArrayCategory.ImageStack) and (len(s) == 2):
        s += [1]
    nbDim = len(s)
    maxNbDim = DataArrayMaxNbDim
    if nbDim > maxNbDim:
        raise ValueError, 'Invalid nb of dimensions: max is %d' % maxNbDim

    dataType = DataType2DataArrayType.get(d.dtype, -1)
    bigEndian = numpy.dtype(d.dtype.byteorder + 'i4') == numpy.dtype('>i4')

    def steps_gen(s):
        size = data.depth() or 1
        for x in s:
            yield size
            size *= x
    t = [i for i in steps_gen(s)]

    s += [0] * (maxNbDim - nbDim)
    t += [0] * (maxNbDim - nbDim)

    #prepare the structure
    dataheader = struct.pack(
        DataArrayPackStr,
        DataArrayMagic,                # 4 bytes I - magic number
        DataArrayVersion,              # 2 bytes H - version
        DataArrayHeaderLen,            # 2 bytes H - this header length
        category,                      # 4 bytes I - category (enum)
        dataType,                      # 4 bytes I - data type (enum)
        bigEndian,                     # 2 bytes H - endianness
        nbDim,                         # 2 bytes H - nb of dims
        s[0],s[1],s[2],s[3],s[4],s[5], # 12 bytes H x 6 - dims
        t[0],t[1],t[2],t[3],t[4],t[5], # 24 bytes I x 6 - stepsbytes
        0, 0)                          # padding 2 x 4 bytes
    if len(dataheader) != DataArrayHeaderLen:
        raise RuntimeError, 'Invalid header len: %d (expected %d)' % \
              (len(dataheader), DataArrayHeaderLen)

    flatData = d.ravel()
    flatData.dtype = numpy.uint8

    dataStr = dataheader + flatData.tostring()        
    release = getattr(data, 'releaseBuffer', None) if force_release_data else None
    if release:
        release()

    return dataStr
