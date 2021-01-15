import fabio
import numpy
import contextlib
import pytest

from Lima.Server.plugins import Utils


class ImageFactory():
    """Factory of images for tests"""

    def __init__(self, tmpdir_factory):
        self._tmpdir_factory = tmpdir_factory

    def edf_image(self, data, header=None) -> str:
        filename = self._tmpdir_factory.mktemp("data").join("img.edf")
        if header is None:
            header = {}
        filename = str(filename)
        image = fabio.edfimage.EdfImage(data, header)
        image.save(filename)
        return image.filename


@pytest.fixture(scope="session")
def image_factory(tmpdir_factory) -> ImageFactory:
    return ImageFactory(tmpdir_factory)


def test_mask(image_factory):
    """
    Test the default Lima behavior
    """
    mask = numpy.zeros((4,4), dtype=numpy.uint8)
    mask[1:3, 1:3] = 1
    filename = image_factory.edf_image(mask)
    internal_mask = Utils.getMaskFromFile(filename)
    numpy.testing.assert_almost_equal(mask, internal_mask.buffer)


def test_mask_zero_flag(image_factory):
    """
    Test the default Lima behavior using the `masked_value` flag
    """
    mask = numpy.ones((4,4), dtype=numpy.uint8)
    mask[1:3, 1:3] = 0
    header = {"masked_value": "zero"}
    filename = image_factory.edf_image(mask, header)
    internal_mask = Utils.getMaskFromFile(filename)
    numpy.testing.assert_almost_equal(mask, internal_mask.buffer)


def test_silx_nonzero_flag(image_factory):
    """
    Test the default silx behavior using the `masked_value` flag
    """
    extected_internal = numpy.zeros((4,4), dtype=numpy.uint8)
    extected_internal[1:3, 1:3] = 1
    mask = numpy.ones((4,4), dtype=numpy.uint8)
    mask[1:3, 1:3] = 0
    header = {"masked_value": "nonzero"}
    filename = image_factory.edf_image(mask, header)
    internal_mask = Utils.getMaskFromFile(filename)
    numpy.testing.assert_almost_equal(extected_internal, internal_mask.buffer)
