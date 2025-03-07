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

import sys
import os
import re
from subprocess import Popen, PIPE
import inspect
import logging
import functools

import PyTango

try:
    import pkg_resources
except ImportError:
    pkg_resources = None


ModDepend = ["Core", "Espia"]
Debug = 0
LimaDir = None
StrictVersionPolicy = None
EnvVersionDepth = {"MAJOR": 1, "MINOR": 2, "FULL": 3}


def get_sub_devices(server=None, cache=True):
    result = {}
    devices = get_device_class_map(server=server, cache=cache)
    for class_name, devices in devices.items():
        result[class_name] = devices[0]
    return result


def get_server_name(argv=None):
    """
    Returns full server name <server_type>/<server_instance>.
    (ex: LimaCCDs/basler01)
    """
    if argv is None:
        argv = sys.argv
    return "LimaCCDs/" + argv[1]


def get_device_class_map(server=None, cache=True):
    """
    Retuns a dict of devices for the given server.
    The dict key is a tango class name and the value is a list of
    devices of that tango class name.

    :param server: full server name (ex: LimaCCDs/basler01)
                   [default: use current process args]
    :type server: str
    :param cache: use last value stored in cache
    :type cache: bool
    :return: Returns dict<tango class name : list of device names>
    :rtype: dict
    """
    global __LIMA_CLASS_MAP
    try:
        dev_map = __LIMA_CLASS_MAP
        if cache:
            return dev_map
    except NameError:
        __LIMA_CLASS_MAP = {}
        dev_map = __LIMA_CLASS_MAP
    if server is None:
        server = get_server_name()
    db = PyTango.Database()
    dev_list = db.get_device_class_list(server)
    for class_name, dev_name in zip(dev_list[1::2], dev_list[::2]):
        dev_names = dev_map.get(class_name)
        if dev_names is None:
            dev_map[class_name] = dev_names = []
        dev_names.append(dev_name)
    return dev_map


def get_lima_device_name(server=None, cache=True):
    """
    Returns LimaCCDs device name for the given server

    :param server: full server name (ex: LimaCCDs/basler01)
                   [default: use current process args]
    :type server: str
    :param cache: use last value stored in cache
    :type cache: bool    
    :return: LimaCCDs tango device name for the given server
    :rtype: str
    """
    return get_device_class_map(server=server, cache=cache)["LimaCCDs"][0]


def get_lima_camera_type(server=None, cache=True):
    """
    Returns the Lima camera type for the given server

    :param server: full server name (ex: LimaCCDs/basler01)
                   [default: use current process args]
    :type server: str
    :param cache: use last value stored in cache
    :type cache: bool    
    :return: the lima camera type for the given server (Ex: Basler)
    :rtype: str
    """
    global __LIMA_CAMERA_TYPE
    try:
        camera_type = __LIMA_CAMERA_TYPE
        if cache:
            return camera_type
    except NameError:
        pass

    lima_dev_name = get_lima_device_name(server=server, cache=cache)
    db = PyTango.Database()
    prop_dict = db.get_device_property(lima_dev_name, "LimaCameraType")
    camera_type = prop_dict["LimaCameraType"]
    if not camera_type:
        raise ValueError("LimaCameraType property not set")
    camera_type = camera_type[0]
    __LIMA_CAMERA_TYPE = camera_type
    return camera_type


def setup_lima_env(argv):
    if is_query_mode(argv):
        return
    if not check_args(argv):
        return
    if not check_link_strict_version():
        return
    server_name = get_server_name(argv)
    try:
        lima_camera_type = get_lima_camera_type(server_name)
    except KeyError:  # first run, maybe wizard creation mode
        return None

    cdir = os.path.join(os.path.dirname(__file__), "camera")
    cfile_name = os.path.join(cdir, lima_camera_type + ".py")
    cfile = open(cfile_name, "rt")
    h = "^[ \t]*"
    p = "(?P<plugin>[A-Za-z0-9_]+)"
    s1 = h + "import[ ]+Lima\\." + p
    s2 = h + "from[ ]+Lima[ ]+import[ ]+" + p
    s3 = h + "from[ ]+Lima\\." + p + "(\\.([A-Za-z0-9_]+))*[ ]+import[ ]+"
    o1, o2, o3 = re.compile(s1), re.compile(s2), re.compile(s3)
    vers = {}
    for l in cfile.readlines():
        m = o1.match(l) or o2.match(l) or o3.match(l)
        if not m:
            continue
        pname = m.group("plugin")
        print_debug("Found %s import in %s" % (pname, cfile_name))
        if pname not in ["Core"]:
            setup_env(pname)
    for k, v in os.environ.items():
        if "LIMA_" in k and "_VERSION" in k and k not in ["LIMA_LINK_STRICT_VERSION"]:
            print_debug("Env: %s=%s" % (k, v))
    return lima_camera_type


def is_query_mode(argv):
    """Returns True if application started with '-?' argument"""
    return "-?" in argv


def check_args(argv):
    global Debug
    for arg in argv:
        if arg.startswith("-v"):
            try:
                Debug = max(0, int(arg[2:]) - 1)
            except:
                pass
    return 1


def check_link_strict_version():
    global StrictVersionPolicy

    cmd = "from Lima import Core; "
    cmd += 'import os; print (os.environ["LIMA_LINK_STRICT_VERSION"])'
    args = ["python", "-c", cmd]
    pobj = Popen(args, stdout=PIPE)
    strict_link = pobj.stdout.readline().strip().upper()
    print_debug("LIMA_LINK_STRICT_VERSION=%s" % strict_link)
    StrictVersionPolicy = None
    pobj.wait()
    if strict_link and strict_link != "NONE":
        StrictVersionPolicy = strict_link
    return StrictVersionPolicy


def setup_env(mod):
    pvers = find_dep_vers(mod)
    all_vers = list(pvers.keys())
    all_vers.sort(version_cmp)
    env_var_name = "LIMA_%s_VERSION" % mod.upper()
    if env_var_name in os.environ:
        ver = os.environ[env_var_name]
        if ver[0] != "v":
            ver = "v" + ver
        filt_vers = [set_env_version_depth(x) for x in all_vers]
        if ver not in filt_vers:
            print("Warning: could not find %s=%s" % (env_var_name, ver))
            return
    else:
        ver = all_vers[-1]
        os.environ[env_var_name] = set_env_version_depth(ver[1:])
    for full_ver, deps in pvers.items():
        if set_env_version_depth(full_ver) == set_env_version_depth(ver):
            break
    for dname, dver in deps.items():
        env_var_name = "LIMA_%s_VERSION" % dname.upper()
        os.environ[env_var_name] = set_env_version_depth(dver)
        if dname != "Core":
            setup_env(dname)


def find_dep_vers(mod):
    vers = {}
    vre_str = "v[0-9]+\.[0-9]+\.[0-9]+"
    vre_obj = re.compile(vre_str)
    pdir = os.path.join(check_lima_dir(), mod)
    for vdir in os.listdir(pdir):
        if vre_obj.match(vdir):
            for dep in ModDepend:
                vname = os.path.join(pdir, vdir, "%s_VERSION" % dep.upper())
                if os.path.exists(vname):
                    vfile = open(vname, "rt")
                    ver = vfile.readline().strip()
                    if vdir not in vers:
                        vers[vdir] = {}
                    vers[vdir][dep] = ver
    print_debug("%s vers=%s" % (mod, vers))
    return vers


def set_env_version_depth(v):
    hasv = v[0] == "v"
    depth = EnvVersionDepth[StrictVersionPolicy]
    env_code = version_code(v)[:depth]
    env_str = ".".join(map(str, env_code))
    if hasv:
        env_str = "v" + env_str
    return env_str


def check_lima_dir():
    global LimaDir
    if LimaDir is not None:
        return LimaDir
    args = ["python", "-c", "from Lima import Core; print (Core.__file__)"]
    pobj = Popen(args, stdout=PIPE)
    core_init_dir = pobj.stdout.readline().strip()
    core_dir = os.path.dirname(core_init_dir)
    LimaDir = os.path.dirname(core_dir)
    pobj.wait()
    return LimaDir


def version_code(s):
    return map(int, s.strip("v").split("."))


def version_cmp(x, y):
    return cmp(version_code(x), version_code(y))


def print_debug(msg):
    if Debug:
        print(msg)


def __get_ct_classes():
    import Lima.Core

    global CT_KLASSES
    try:
        return CT_KLASSES
    except NameError:
        pass

    classes = {}
    for member_name in dir(Lima.Core):
        if not member_name.startswith("Ct"):
            continue
        member = getattr(Lima.Core, member_name)
        if not inspect.isclass(member):
            continue
        classes[member_name] = member
    CT_KLASSES = classes
    return classes


def __filter(obj, tango_class_name, member_name, member):
    import Lima.Core

    # Avoid enumerations
    is_enum = type(type(member)) == type(Lima.Core.CtControl.CameraErrorCode)
    if is_enum and member_name[0].isupper():
        return False
    return True


def __to_lower_separator(text, sep="_"):
    r = text[0].lower()
    for c in text[1:]:
        if c.isupper():
            r += sep
            c = c.lower()
        r += c
    return r


def to_tango_object(ct, name_id):
    """
    Create an adapter for CtControl, CtImage, CtSaving, etc that
    has attributes. Example: CtImage has a getRoi and setRoi methods.
    The returned object will have them as well, plus a python roi
    property.
    """
    global CT_TANGO_MAP
    try:
        ct_tango_map = CT_TANGO_MAP
    except NameError:
        ct_tango_map = CT_TANGO_MAP = {}

    ct_klass = ct.__class__
    klass = ct_tango_map.get(ct_klass)
    if klass:
        return klass(ct)

    ct_klass_name = ct_klass.__name__

    def getter(obj, name=None):
        ct = obj.__dict__["__ct"]
        return getattr(ct, name)()

    def setter(obj, value, name=None):
        ct = obj.__dict__["__ct"]
        return getattr(ct, name)(value)

    patched_members = {}
    for member_name in dir(ct_klass):
        # skip non "get" members
        if not member_name.startswith("get"):
            continue

        _fget = getattr(ct_klass, member_name)

        # skip non callables
        if not callable(_fget):
            continue

        name = member_name[3:]
        fget_name = member_name
        fset_name = "set" + name
        name_lower_us = __to_lower_separator(name)
        fget_name = member_name

        fget = functools.partial(getter, name=fget_name)

        if hasattr(ct_klass, fset_name):
            fset = functools.partial(setter, name=fset_name)
        else:
            fset = None

        logging.debug("added artificial member %s.%s", ct_klass.__name__, name_lower_us)
        patched_members[name_lower_us] = fget, fset

    keys = patched_members.keys()

    class klass(object):
        def __init__(self, ct, name):
            self.__dict__["__ct"] = ct
            self.__dict__["__name"] = name

        def __getattr__(self, name):
            return getattr(self.__dict__["__ct"], name)

        def __setattr__(self, name, value):
            if hasattr(self, name):
                return object.__setattr__(self, name, value)
            return setattr(self.__dict__["__ct"], name, value)

        def __dir__(self):
            return dir(self.__dict__["__ct"]) + list(keys)

        def __reduce__(self):
            import PyTango.client

            db = PyTango.Util.instance().get_database()
            name = "{0}:{1}/{2}".format(
                db.get_db_host(), db.get_db_port(), self.__dict__["__name"]
            )
            return PyTango.client._Device, (name,)

    klass.__name__ = ct_klass_name
    ct_tango_map[ct_klass] = klass
    kl = klass(ct, name_id)
    for name, value in patched_members.items():
        setattr(kl, name, property(*value))
    return kl


def _import(name):
    __import__(name)
    return sys.modules[name]


def get_entry_point(group, name):
    # try to find an extension using setuptools entry points
    if pkg_resources is None:
        return None
    entry_points = tuple(pkg_resources.iter_entry_points(group, name))
    if not entry_points:
        return None
    elif len(entry_points) > 1:
        raise ValueError("found more than one entry point matching {}".format(name))
    return entry_points[0]


def get_camera_module(name):
    """Returns the python module for the given camera type"""
    entry_point = get_entry_point("Lima_tango_camera", name)
    if entry_point is None:
        # fallback to search in local camera directory
        mod_name = "Lima.Server.camera.{}".format(name)
        return _import(mod_name)
    return entry_point.load()


def get_plugin_module(name):
    """Returns the python module for the given plugin type"""
    entry_point = get_entry_point("Lima_tango_plugin", name)
    if entry_point is None:
        # fallback to search in local plugins directory
        mod_name = "Lima.Server.plugins.{}".format(name)
        return _import(mod_name)
    return entry_point.load()
