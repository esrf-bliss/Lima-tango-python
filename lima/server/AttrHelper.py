############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2022
# European Synchrotron Radiation Facility
# CS40220 38043 Grenoble Cedex 9
# FRANCE
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


# ============================================================================
#                              HELPERS
# ============================================================================
#
# These helpers allows any one to map attributes with the LIMA interfaces commands without having
# to write any extra code for the read_ / write_ methods.
# It works for attributes with enumerate value and for simple value passing.
# Mapping between attributes and commands is done using a dictionnary and for each
# attribute with enum an extra dictionnary is mandatory. e.g for Andor camera we could have:
#         self.__FastTrigger = {'ON':True,
#                           'OFF':False}
#        self.__Cooler = {'ON': True,
#                             'OFF': False}
#        self.__ShutterLevel = {'LOW':0,
#                                   'HIGH':1}
#        self.__Attribute2FunctionBase = {'fast_trigger': 'FastExtTrigger',
#                                         'shutter_level': 'ShutterLevel',
#                                         'temperature': 'Temperature',
#                                         'temperature_sp': 'TemperatureSP',
#                                         'cooler': 'Cooler',
#                                         'cooling_status': 'CoolingStatus',
#                                         }
# __Attribute2FunctionBase dict. maps attributes and commands (e.g. fast_trigger --> setFastExtTrigger and getFastExtTrigger)
# __FasTrigger dict. is the enum list for the attribute fast_trigger. Naming convention supposes the attribute name composed
# with words separated by "_" and the enum dictionnary name is composed with the same words titled.
#
# Finally you will need to overload your __getattr__ class method and to call the help function get_attr_4u e.g:
#
# def __getattr__(self, name):
#       return get_attr_4u(self, name, _AndorCamera)
#

import PyTango


def getDictKey(dict, value):
    try:
        ind = list(dict.values()).index(value)
    except ValueError:
        return None
    return list(dict.keys())[ind]


def getDictValue(dict, key):
    try:
        value = dict[key.upper()]
    except KeyError:
        return None
    return value


# preserve the case of key
def getDictCaseValue(dict, key):
    try:
        value = dict[key]
    except KeyError:
        return None
    return value


## @brief Class for genenic read_<attribute> with enum value
class CallableReadEnum:
    def __init__(self, dictionnary, func2Call):
        self.__dict = dictionnary
        self.__func2Call = func2Call

    def __call__(self, attr):
        value = getDictKey(self.__dict, self.__func2Call())
        attr.set_value(value)


## @brief Class for genenic write_<attribute> with enum value
class CallableWriteEnum:
    def __init__(self, attr_name, dictionnary, func2Call):
        self.__attr_name = attr_name
        self.__dict = dictionnary
        self.__func2Call = func2Call

    def __call__(self, attr):
        data = attr.get_write_value()
        value = getDictValue(self.__dict, data.upper())
        if value is None:
            PyTango.Except.throw_exception(
                "WrongData",
                "Wrong value %s: %s" % (self.__attr_name, data.upper()),
                "LimaCCD Class",
            )
        else:
            self.__func2Call(value)


## @brief Class for genenic read_<attribute> with simple value
class CallableRead:
    def __init__(self, func2Call):
        self.__func2Call = func2Call

    def __call__(self, attr):
        value = self.__func2Call()
        attr.set_value(value)


## @brief Class for genenic write_<attribute> with simple value
class CallableWrite:
    def __init__(self, attr_name, func2Call):
        self.__attr_name = attr_name
        self.__func2Call = func2Call

    def __call__(self, attr):
        value = attr.get_write_value()
        if value is None:
            PyTango.Except.throw_exception(
                "WrongData",
                "Wrong value %s: %s" % (self.__attr_name, data.upper()),
                "LimaCCD Class",
            )
        else:
            self.__func2Call(value)


## @brief helper for automatic attribute to command mapping
# To be called from __getattr__
# if update_dict is True the __dict__ is updated for the new attribute
# means for next call to the attr will not pass through this helper but will get
# the callable object from the __dict_ object dictionnary.
# set update_dict to False to avoid keep reference of some objects you want to delete
def get_attr_4u(obj, name, interface, update_dict=True):

    if name.startswith("read_") or name.startswith("write_"):
        split_name = name.split("_")[1:]
        attr_name = "".join([x.title() for x in split_name])
        # Look for a public attribute first (available in inherited classes)
        d = getattr(obj, "_" + attr_name, None)
        if d is None:
            dict_name = "_" + obj.__class__.__name__ + "__" + attr_name
            d = getattr(obj, dict_name, None)
        dict_name = "_" + obj.__class__.__name__ + "__Attribute2FunctionBase"
        dict_name = getattr(obj, dict_name, None)
        if dict_name:
            attr_name = dict_name.get("_".join(split_name), attr_name)

        if d:
            if name.startswith("read_"):
                functionName = "get" + attr_name
                function2Call = getattr(interface, functionName)
                callable_obj = CallableReadEnum(d, function2Call)
            else:
                functionName = "set" + attr_name
                function2Call = getattr(interface, functionName)
                callable_obj = CallableWriteEnum("_".join(split_name), d, function2Call)

        else:
            if name.startswith("read_"):
                functionName = "get" + attr_name
                function2Call = getattr(interface, functionName)
                callable_obj = CallableRead(function2Call)
            else:
                functionName = "set" + attr_name
                function2Call = getattr(interface, functionName)
                callable_obj = CallableWrite("_".join(split_name), function2Call)

        if update_dict:
            obj.__dict__[name] = callable_obj
        callable_obj.__name__ = name
        if not hasattr(callable_obj, "__annotations__"):
            callable_obj.__annotations__ = dict()
        return callable_obj

    raise AttributeError("%s has no attribute %s" % (obj.__class__.__name__, name))


## @brief return list of posible value for attribute name
def get_attr_string_value_list(obj, attr_name):
    valueList = []
    dict_name = (
        "_"
        + obj.__class__.__name__
        + "__"
        + "".join([x.title() for x in attr_name.split("_")])
    )
    d = getattr(obj, dict_name, None)
    if d:
        valueList = list(d.keys())
    return valueList


# ============================================================================
#                    tango.server (high-level API) replacement
# ============================================================================
#
# make_fget_fset() is the high-level-API equivalent of get_attr_4u() above:
# it builds a static (fget, fset) pair for `tango.server.attribute(...)`,
# dispatching to `getName`/`setName` on the first of `interfaces` that has it,
# by the same naming convention (attr_name -> CamelCase -> getCamelCase).
#
# Unlike get_attr_4u, `interfaces` are resolved *per call* through unary
# callables taking the device instance, since a high-level `attribute()` is
# built once at class-definition time, before any device instance exists:
#
#   grow_factor = attribute(
#       dtype=float, access=AttrWriteType.READ_WRITE,
#       fget=(fget := make_fget_fset("grow_factor", lambda self: self._SimuCamera)[0]),
#   )
#
# or, more commonly, unpacking both at once:
#
#   _fget, _fset = make_fget_fset(
#       "mode", lambda self: self._SimuCamera.getFrameGetter(),
#       lambda self: self._SimuCamera, enum=_Mode,
#   )
#   mode_attr = attribute(name="mode", dtype=str, access=AttrWriteType.READ_WRITE,
#                          fget=_fget, fset=_fset)
#
# A plain-assignment `attribute(name=..., fget=..., fset=...)` (not a method
# decorator) is used on purpose: several of these attributes share their name
# with a `device_property` of the same name (the property is only consulted
# once, at init_device, for the initial hardware config), and only
# `attribute(name=...)` lets the Tango-visible name be decoupled from the
# Python identifier - `device_property()` has no such override.


def _title_case(attr_name):
    return "".join(x.title() for x in attr_name.split("_"))


def make_fget_fset(attr_name, *interfaces, enum=None):
    """Build (fget, fset) callables for `tango.server.attribute(fget=, fset=)`.

    Arguments:
        attr_name: attribute name, e.g. "grow_factor" -> getGrowFactor/setGrowFactor
        interfaces: one or more `f(device_self) -> target_object` callables,
            tried in order; the first whose target has getX/setX is used
            (mirrors get_attr_4u + the legacy try/except interface fallback)
        enum: optional {"STRING_KEY": underlying_value} dict for string-valued
            attributes, translated both ways (mirrors the legacy per-attribute
            enum dict convention, e.g. self.__Mode)
    """
    camel = _title_case(attr_name)
    get_name, set_name = "get" + camel, "set" + camel

    def _resolve_target(device_self):
        last_exc = None
        for make_target in interfaces:
            try:
                target = make_target(device_self)
            except Exception as exc:
                last_exc = exc
                continue
            if hasattr(target, get_name) or hasattr(target, set_name):
                return target
        if last_exc is not None:
            raise last_exc
        raise AttributeError(
            "No %s/%s found for attribute %r" % (get_name, set_name, attr_name)
        )

    def fget(device_self):
        value = getattr(_resolve_target(device_self), get_name)()
        return getDictKey(enum, value) if enum else value

    def fset(device_self, value):
        if enum:
            resolved = getDictValue(enum, value.upper())
            if resolved is None:
                import tango

                tango.Except.throw_exception(
                    "WrongData",
                    "Wrong value %s: %s" % (attr_name, value.upper()),
                    "LimaCCD Class",
                )
            value = resolved
        getattr(_resolve_target(device_self), set_name)(value)

    return fget, fset
