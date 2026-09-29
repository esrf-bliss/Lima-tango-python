############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2026
# European Synchrotron Radiation Facility
# CS40220 38043 Grenoble Cedex 9
# FRANCE
#
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
"""
Low-latency H264/WebRTC video streaming plugin for the LimaCCDs device server.

Polls CtVideo's getLastImage()/getLastImageCounter() directly (in-process,
no Tango round trip) so frames only cross into Tango for the one-shot WebRTC
SDP signaling handshake, never for the per-frame media path. CtVideo only
supports a single registered ImageCallback and LimaCCDs.py already occupies
it for video_last_image push events, so polling the same accessor
LimaCCDs.py itself uses is what allows this to coexist with it. Frames are
only available while the main LimaCCDs device has video_live=True, since
that is what drives the camera's video acquisition in the first place.

Requires the optional dependencies ``aiortc``, ``av`` (PyAV) and ``Pillow``.
"""

import asyncio
import io
import threading
import time
import traceback
import uuid
from fractions import Fraction

import numpy
import PyTango

from lima import core
from lima.server.plugins.Utils import BasePostProcess


def _debug_log(msg):
    # Bypasses Tango's own logging (level, omniORB thread attachment) so the
    # poll loop's behaviour can be observed unambiguously - a single place to
    # disable (e.g. make a no-op) once no longer needed.
    print("H264VideoStream: %s" % msg)


try:
    import av
except ImportError:
    av = None

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

try:
    from aiortc import (
        MediaStreamTrack,
        RTCConfiguration,
        RTCIceServer,
        RTCPeerConnection,
        RTCSessionDescription,
    )
except ImportError:
    MediaStreamTrack = object
    RTCConfiguration = RTCIceServer = RTCPeerConnection = RTCSessionDescription = None


# Only the VideoMode values Basler (and video-capable cameras in general) can
# actually emit are mapped; ffmpeg's native bayer_* pixel formats let
# libswscale do demosaicing as part of the yuv420p/rgb24 conversion below, so
# no custom debayering code is needed.
_VIDEO_MODE_TO_AV_FORMAT_NAMES = {
    "Y8": "gray",
    "Y16": "gray16le",
    "RGB24": "rgb24",
    "BGR24": "bgr24",
    "RGB32": "rgba",
    "BGR32": "bgra",
    "BAYER_RG8": "bayer_rggb8",
    "BAYER_RG16": "bayer_rggb16le",
    "BAYER_BG8": "bayer_bggr8",
    "BAYER_BG16": "bayer_bggr16le",
}


def _build_video_mode_table():
    table = {}
    for mode_name, av_format in _VIDEO_MODE_TO_AV_FORMAT_NAMES.items():
        mode = getattr(core.VideoMode, mode_name, None)
        if mode is not None:
            table[mode] = av_format
    return table


# 16-bit-container video modes: the camera's actual sensor depth (e.g. a
# Basler 12-bit sensor reported as BAYER_RG16) can be less than 16 bits, with
# the raw values left unscaled in the low bits of each 16-bit sample - same
# issue and fix (data << (16 - bpp)) independently implemented by both
# daiquiri's parse_video_frame() and video-streamer-mpeg's CameraBase.frame().
_SIXTEEN_BIT_AV_FORMATS = frozenset({"gray16le", "bayer_rggb16le", "bayer_bggr16le"})


def _build_image_type_to_bpp_table():
    table = {}
    for bpp in (8, 10, 12, 14, 16):
        image_type = getattr(core.ImageType, "Bpp%d" % bpp, None)
        if image_type is not None:
            table[image_type] = bpp
    return table


def _set_result_if_pending(future, value):
    if not future.done():
        future.set_result(value)


def _missing_dependencies(**modules):
    # Reports exactly which import(s) failed, since av/aiortc/Pillow are
    # independent and any one of them can be missing without the others.
    return [name for name, mod in modules.items() if mod is None]


def _filter_sdp_candidates(sdp, keep_address):
    # aioice enumerates every local interface for host candidates (no
    # built-in way to exclude one, e.g. a Docker bridge - see
    # https://github.com/aiortc/aioice/issues/2), so unwanted ones are
    # dropped here instead. No-op when keep_address is unset.
    if not keep_address:
        return sdp
    lines = []
    for line in sdp.split("\r\n"):
        if line.startswith("a=candidate:"):
            fields_ = line.split()
            if len(fields_) > 4 and fields_[4] != keep_address:
                continue
        lines.append(line)
    return "\r\n".join(lines)


class _LatestFrameBox:
    """Hands the newest av.VideoFrame from the Lima callback thread to the
    asyncio loop, dropping anything older rather than queueing it."""

    def __init__(self, loop):
        self.__loop = loop
        self.__lock = threading.Lock()
        self.__frame = None
        self.__waiters = []

    def publish(self, frame):
        with self.__lock:
            self.__frame = frame
            waiters, self.__waiters = self.__waiters, []
        for future in waiters:
            self.__loop.call_soon_threadsafe(_set_result_if_pending, future, frame)

    async def wait_for_frame(self):
        with self.__lock:
            if self.__frame is not None:
                return self.__frame
            future = self.__loop.create_future()
            self.__waiters.append(future)
        return await future


class LimaVideoStreamTrack(MediaStreamTrack):
    kind = "video"

    _CLOCK_RATE = 90000

    def __init__(self, frame_box):
        super().__init__()
        self.__frame_box = frame_box
        self.__start_time = None
        self.__time_base = Fraction(1, self._CLOCK_RATE)
        self.__logged_first_recv = False

    async def recv(self):
        frame = await self.__frame_box.wait_for_frame()
        if self.__start_time is None:
            self.__start_time = time.time()
        frame.pts = int((time.time() - self.__start_time) * self._CLOCK_RATE)
        frame.time_base = self.__time_base
        if not self.__logged_first_recv:
            self.__logged_first_recv = True
            _debug_log(
                "aiortc pulled its first frame from the track (%dx%d)"
                % (frame.width, frame.height)
            )
        return frame


class H264VideoStreamDeviceServer(BasePostProcess):
    core.DEB_CLASS(core.DebModule.DebModApplication, "H264VideoStreamDeviceServer")

    VIDEO_MODE_TO_AV_FORMAT = _build_video_mode_table()
    IMAGE_TYPE_TO_BPP = _build_image_type_to_bpp_table()

    def __init__(self, cl, name):
        self.__raw_lock = threading.Lock()
        self.__raw_frame = None  # (buffer, av_format, width, height, frame_number)

        self.__snapshot_lock = threading.Lock()
        self.__snapshot_bytes = None
        self.__snapshot_format = None
        self.__snapshot_counter = 0

        self.__stream_max_fps = 24.0
        self.__logged_av_format = False
        self.__logged_bpp_scaling = False
        self.__logged_frame_stats = False

        self.__peer_connections = {}
        self.__loop = None
        self.__loop_thread = None
        self.__frame_box = None
        self.__track = None
        self.__poll_task = None

        BasePostProcess.__init__(self, cl, name)
        H264VideoStreamDeviceServer.init_device(self)

    @core.DEB_MEMBER_FUNCT
    def init_device(self):
        _debug_log("init_device: entered")
        BasePostProcess.init_device(self)

        self.__loop = asyncio.new_event_loop()

        def _run_loop():
            _debug_log("loop thread: starting")
            try:
                # Tango device methods (warn_stream, push_change_event,
                # attribute access) silently no-op when called from a thread
                # never attached to omniORB, so the loop must run inside
                # EnsureOmniThread.
                with PyTango.EnsureOmniThread():
                    _debug_log("loop thread: inside EnsureOmniThread, calling run_forever")
                    self.__loop.run_forever()
                _debug_log("loop thread: run_forever returned")
            except Exception:
                _debug_log("loop thread: crashed: %s" % traceback.format_exc())

        self.__loop_thread = threading.Thread(target=_run_loop, daemon=True)
        self.__loop_thread.start()

        self.__frame_box = _LatestFrameBox(self.__loop)
        self.__track = LimaVideoStreamTrack(self.__frame_box)

        ctControl = _control_ref()
        self.__video = ctControl.video()
        self.__image = ctControl.image()
        # CtVideo only supports a single registered ImageCallback, and
        # LimaCCDs.py already occupies it for video_last_image push events,
        # so new frames are picked up by polling getLastImage()/
        # getLastImageCounter() instead - the same accessor LimaCCDs.py
        # itself uses for reading video_last_image, safe for concurrent use.
        _debug_log("init_device: scheduling poll task")
        self.__poll_task = asyncio.run_coroutine_threadsafe(self.__poll_video(), self.__loop)
        _debug_log("init_device: poll task scheduled, done=%s" % self.__poll_task.done())

    async def __poll_video(self):
        _debug_log("poll_video: coroutine entered")
        self.warn_stream("H264VideoStream: poll loop started")
        last_counter = -1
        while True:
            # Everything is inside the try, including the sleep/fps setup -
            # any uncaught exception here previously killed this coroutine
            # permanently and silently, since self.__poll_task's result is
            # never awaited/checked anywhere.
            try:
                fps = self.__stream_max_fps if self.__stream_max_fps > 0 else 30.0
                await asyncio.sleep(1.0 / fps)
                counter = self.__video.getLastImageCounter()
                if counter == last_counter:
                    continue
                last_counter = counter
                self._on_new_video_image(self.__video.getLastImage())
            except Exception:
                _debug_log("poll_video: exception: %s" % traceback.format_exc())
                self.warn_stream(
                    "H264VideoStream: failed to poll last video image: %s"
                    % traceback.format_exc()
                )

    @core.DEB_MEMBER_FUNCT
    def delete_device(self):
        _debug_log(
            "delete_device: entered, call stack:\n%s"
            % "".join(traceback.format_stack())
        )
        if self.__poll_task is not None:
            self.__poll_task.cancel()
        if self.__loop is not None:
            for pc in list(self.__peer_connections.values()):
                asyncio.run_coroutine_threadsafe(pc.close(), self.__loop)
            self.__loop.call_soon_threadsafe(self.__loop.stop)
            self.__loop_thread.join(timeout=5)

    def __run_coroutine(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.__loop).result()

    def __rtc_configuration(self):
        if RTCIceServer is None or not self.IceServers:
            return RTCConfiguration(iceServers=[])
        return RTCConfiguration(iceServers=[RTCIceServer(urls=u) for u in self.IceServers])

    # ------------------------------------------------------------------
    #    Frame ingestion (called from the Lima video callback thread)
    # ------------------------------------------------------------------
    def _on_new_video_image(self, image):
        av_format = self.VIDEO_MODE_TO_AV_FORMAT.get(image.mode())
        if not self.__logged_av_format:
            self.__logged_av_format = True
            _debug_log(
                "image.mode()=%s -> av_format=%s, image_type=%s"
                % (image.mode(), av_format, self.__image.getImageType())
            )
            self.warn_stream(
                "H264VideoStream: image.mode()=%s -> av_format=%s, image_type=%s"
                % (image.mode(), av_format, self.__image.getImageType())
            )
        if av_format is None:
            self.warn_stream("H264VideoStream: unsupported video mode %s" % image.mode())
            return

        buffer = image.buffer()
        if not buffer:
            return

        if av_format in _SIXTEEN_BIT_AV_FORMATS:
            bpp = self.IMAGE_TYPE_TO_BPP.get(self.__image.getImageType())
            if not self.__logged_bpp_scaling:
                self.__logged_bpp_scaling = True
                _debug_log(
                    "image_type=%s -> bpp=%s (scaling %s)"
                    % (self.__image.getImageType(), bpp, "applied" if bpp and bpp < 16 else "skipped")
                )
                self.warn_stream(
                    "H264VideoStream: image_type=%s -> bpp=%s (scaling %s)"
                    % (self.__image.getImageType(), bpp, "applied" if bpp and bpp < 16 else "skipped")
                )
            if bpp is not None and bpp < 16:
                # e.g. a 12-bit sensor reported as BAYER_RG16 leaves values
                # unscaled in the low bits of each 16-bit sample, which
                # renders as near-black without this.
                buffer = (numpy.frombuffer(buffer, dtype="<u2") << numpy.uint16(16 - bpp)).astype("<u2").tobytes()

        with self.__raw_lock:
            self.__raw_frame = (buffer, av_format, image.width(), image.height(), image.frameNumber())

        # Skip the yuv420p conversion cost entirely when nobody is watching;
        # the poll loop's own interval already caps how often this runs.
        if not self.__peer_connections:
            return

        try:
            src_frame = av.VideoFrame(width=image.width(), height=image.height(), format=av_format)
            src_frame.planes[0].update(buffer)
            width, height = self.__target_stream_size(image.width(), image.height())
            stream_frame = src_frame.reformat(width=width, height=height, format="yuv420p")
        except Exception:
            _debug_log("failed to convert frame to yuv420p: %s" % traceback.format_exc())
            self.warn_stream("H264VideoStream: failed to convert frame to yuv420p")
            return

        if not self.__logged_frame_stats:
            self.__logged_frame_stats = True
            raw_arr = numpy.frombuffer(buffer, dtype="<u2")
            y_arr = numpy.frombuffer(bytes(stream_frame.planes[0]), dtype=numpy.uint8)
            _debug_log(
                "frame stats: raw(post-scale) min=%d max=%d, yuv Y-plane min=%d max=%d"
                % (raw_arr.min(), raw_arr.max(), y_arr.min(), y_arr.max())
            )

        self.__frame_box.publish(stream_frame)

    def __target_stream_size(self, width, height):
        max_w, max_h = self.MaxStreamWidth, self.MaxStreamHeight
        if max_w <= 0 or max_h <= 0 or (width <= max_w and height <= max_h):
            return width, height
        scale = min(max_w / width, max_h / height)
        # even dimensions are required by yuv420p's 2x2 chroma subsampling
        return int(width * scale) & ~1, int(height * scale) & ~1

    # ------------------------------------------------------------------
    #    WebRTC signaling commands
    # ------------------------------------------------------------------
    @core.DEB_MEMBER_FUNCT
    def JoinStream(self, offer_sdp):
        missing = _missing_dependencies(aiortc=RTCPeerConnection, av=av)
        if missing:
            PyTango.Except.throw_exception(
                "MissingDependency",
                "Missing Python package(s) required by H264VideoStream: %s" % ", ".join(missing),
                "JoinStream",
            )

        # uuid4() is plain Python (no event loop needed), safe to call on
        # this Tango command thread; everything aiortc-related below is not
        # and must run on self.__loop's own thread instead (see negotiate()).
        connection_id = str(uuid.uuid4())

        async def negotiate():
            pc = RTCPeerConnection(configuration=self.__rtc_configuration())
            pc.addTrack(self.__track)
            self.__peer_connections[connection_id] = pc

            # A client is not guaranteed to call LeaveStream (crash, network
            # drop, ...), so connectionstatechange is the actual source of
            # truth: closed/failed are terminal, disconnected can recover
            # from a brief network blip so it only triggers cleanup after it
            # has stayed disconnected for DisconnectTimeout seconds.
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                if pc.connectionState in ("failed", "closed"):
                    await self.__cleanup_connection(connection_id)
                elif pc.connectionState == "disconnected":
                    await asyncio.sleep(self.DisconnectTimeout)
                    if pc.connectionState == "disconnected":
                        await self.__cleanup_connection(connection_id)

            offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            unfiltered_sdp = pc.localDescription.sdp
            filtered_sdp = _filter_sdp_candidates(unfiltered_sdp, self.IceHostAddress)
            if self.IceHostAddress:
                dropped = unfiltered_sdp.count("a=candidate:") - filtered_sdp.count("a=candidate:")
                self.warn_stream(
                    "H264VideoStream: IceHostAddress=%s, dropped %d other ICE candidate(s)"
                    % (self.IceHostAddress, dropped)
                )
            return filtered_sdp

        try:
            answer_sdp = self.__run_coroutine(negotiate())
        except Exception:
            self.__peer_connections.pop(connection_id, None)
            raise

        return [connection_id, answer_sdp]

    @core.DEB_MEMBER_FUNCT
    def LeaveStream(self, connection_id):
        asyncio.run_coroutine_threadsafe(
            self.__cleanup_connection(connection_id), self.__loop
        )

    async def __cleanup_connection(self, connection_id):
        pc = self.__peer_connections.pop(connection_id, None)
        if pc is not None:
            await pc.close()

    # ------------------------------------------------------------------
    #    Full-size snapshot command + attribute
    # ------------------------------------------------------------------
    @core.DEB_MEMBER_FUNCT
    def SaveLastVideoImage(self, argin):
        missing = _missing_dependencies(av=av, Pillow=PILImage)
        if missing:
            PyTango.Except.throw_exception(
                "MissingDependency",
                "Missing Python package(s) required by SaveLastVideoImage: %s" % ", ".join(missing),
                "SaveLastVideoImage",
            )

        image_format = "JPEG"
        quality = self.JpegQuality
        if argin:
            parts = argin.split(":")
            image_format = parts[0].upper()
            if len(parts) > 1:
                quality = int(parts[1])
        if image_format not in ("JPEG", "PNG"):
            PyTango.Except.throw_exception(
                "BadArgument", "format must be 'JPEG', 'PNG' or 'JPEG:<quality>'", "SaveLastVideoImage"
            )

        with self.__raw_lock:
            raw = self.__raw_frame
        if raw is None:
            PyTango.Except.throw_exception("NoImage", "No video frame received yet", "SaveLastVideoImage")
        buffer, av_format, width, height, frame_number = raw

        src_frame = av.VideoFrame(width=width, height=height, format=av_format)
        src_frame.planes[0].update(buffer)
        rgb_array = src_frame.reformat(format="rgb24").to_ndarray()

        out = io.BytesIO()
        pil_image = PILImage.fromarray(rgb_array)
        if image_format == "JPEG":
            pil_image.save(out, format="JPEG", quality=quality)
        else:
            pil_image.save(out, format="PNG")

        with self.__snapshot_lock:
            self.__snapshot_bytes = out.getvalue()
            self.__snapshot_format = image_format
            self.__snapshot_counter = frame_number

    def read_last_video_image_snapshot(self, attr):
        with self.__snapshot_lock:
            data, image_format = self.__snapshot_bytes, self.__snapshot_format
        if data is None:
            PyTango.Except.throw_exception(
                "NoImage", "SaveLastVideoImage has not been called yet", "read_last_video_image_snapshot"
            )
        attr.set_value(image_format, data)

    def read_last_video_image_snapshot_counter(self, attr):
        with self.__snapshot_lock:
            attr.set_value(self.__snapshot_counter)

    def read_stream_max_fps(self, attr):
        attr.set_value(self.__stream_max_fps)

    def write_stream_max_fps(self, attr):
        self.__stream_max_fps = attr.get_write_value()


class H264VideoStreamDeviceServerClass(PyTango.DeviceClass):

    class_property_list = {}

    device_property_list = {
        "MaxStreamWidth": [
            PyTango.DevLong,
            "Downscale streamed frames wider than this (0 = no limit, does not affect SaveLastVideoImage)",
            [0],
        ],
        "MaxStreamHeight": [
            PyTango.DevLong,
            "Downscale streamed frames taller than this (0 = no limit, does not affect SaveLastVideoImage)",
            [0],
        ],
        "IceServers": [
            PyTango.DevVarStringArray,
            "STUN/TURN server URLs for WebRTC ICE negotiation (empty is fine on a single network segment)",
            [],
        ],
        "JpegQuality": [
            PyTango.DevShort,
            "Default JPEG quality (1-100) used by SaveLastVideoImage when none is given",
            [90],
        ],
        "DisconnectTimeout": [
            PyTango.DevDouble,
            "Seconds a WebRTC connection may stay in 'disconnected' state before it is force-closed, in case LeaveStream is never called",
            [30.0],
        ],
        "IceHostAddress": [
            PyTango.DevString,
            "If set, only advertise this IP as a host ICE candidate to viewers, dropping any others (e.g. a Docker bridge interface also present on this machine)",
            [""],
        ],
    }

    cmd_list = {
        "JoinStream": [
            [PyTango.DevString, "WebRTC SDP offer"],
            [PyTango.DevVarStringArray, "[connection_id, WebRTC SDP answer]"],
        ],
        "LeaveStream": [
            [PyTango.DevString, "connection_id returned by JoinStream"],
            [PyTango.DevVoid, ""],
        ],
        "SaveLastVideoImage": [
            [PyTango.DevString, "'JPEG', 'PNG' or 'JPEG:<quality>'"],
            [PyTango.DevVoid, ""],
        ],
        "Start": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
        "Stop": [[PyTango.DevVoid, ""], [PyTango.DevVoid, ""]],
    }

    attr_list = {
        "RunLevel": [[PyTango.DevLong, PyTango.SCALAR, PyTango.READ_WRITE]],
        "last_video_image_snapshot": [
            [PyTango.DevEncoded, PyTango.SCALAR, PyTango.READ],
            {
                "label": "Last snapshot",
                "description": "Full-size video frame captured by SaveLastVideoImage, as JPEG or PNG bytes",
            },
        ],
        "last_video_image_snapshot_counter": [
            [PyTango.DevLong64, PyTango.SCALAR, PyTango.READ],
            {
                "label": "Snapshot source frame number",
                "description": "video_last_image_counter value of the frame the last snapshot was built from",
            },
        ],
        "stream_max_fps": [
            [PyTango.DevDouble, PyTango.SCALAR, PyTango.READ_WRITE],
            {
                "label": "Stream max FPS",
                "description": "Caps how often video frames are converted/encoded for WebRTC viewers (0 = no cap)",
                "unit": "Hz",
            },
        ],
    }

    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


_control_ref = None


def set_control_ref(control_class_ref):
    global _control_ref
    _control_ref = control_class_ref


def get_tango_specific_class_n_device():
    return H264VideoStreamDeviceServerClass, H264VideoStreamDeviceServer
