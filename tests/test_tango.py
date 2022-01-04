"""
Test the Device server Tango API
"""

import numpy
import time
import logging
from unittest import mock
import pytest
from Lima import Core
from Lima.Server import LimaCCDs


_logger = logging.getLogger(__name__)


class MockedLimaCCDs(LimaCCDs.LimaCCDs):

    def __init__(self, properties=None):
        """
        Attributes:
            properties: Simulate the tango device properties
        """
        self.__properties = properties
        if properties is None:
            properties = {}
        for k, v in LimaCCDs.LimaCCDsClass.device_property_list.items():
            v = v[2]
            if isinstance(v, list):
                if len(v) > 0:
                    v = v[0]
                setattr(self, k, v)
        for k, v in properties.items():
            setattr(self, k, v)
        with mock.patch('PyTango.LatestDeviceImpl.__init__'):
            with mock.patch('PyTango.Database'):
                with mock.patch('Lima.Server.LimaCCDs._get_control') as control:
                    super(MockedLimaCCDs, self).__init__()

    def add_attribute(self, prop, getter, setter):
        pass

    def get_device_attr(self):
        return mock.Mock()

    def set_state(self, state):
        self.__state = state

    def get_device_properties(self, ds_class=None):
        pass


def test_imageopmode_device_prop():
    """Setup the mode from tango properties

    Check that the mode was set
    """
    properties = {"ImageOpMode": "SoftOnly"}
    tango = MockedLimaCCDs(properties)
    control = tango._LimaCCDs__control
    assert control is not None
    assert control.image().setMode.call_count == 1
    assert control.image().setMode.call_args[0][0] == Core.CtImage.SoftOnly


def test_imageopmode_wrong_prop():
    """Setup the mode from tango properties

    Check that the mode was set
    """
    properties = {"ImageOpMode": "Foo"}
    tango = MockedLimaCCDs(properties)
    control = tango._LimaCCDs__control
    assert control is not None
    assert control.image().setMode.call_count == 0
