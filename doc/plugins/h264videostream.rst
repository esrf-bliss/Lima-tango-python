H264VideoStream
================

A plugin device that streams the camera's live video feed as H264 over
WebRTC, and can grab a full-size JPEG/PNG snapshot on demand.

Rather than a client polling the main ``LimaCCDs`` device's
``video_last_image`` attribute over Tango, this plugin polls
``CtVideo.getLastImage()``/``getLastImageCounter()`` directly, in the
same process as ``LimaCCDs`` — the same accessor ``LimaCCDs.py`` itself
uses for that attribute. Per-frame data never goes through Tango — only
the one-time WebRTC signaling handshake does. It cannot instead register
its own ``CtVideo`` image callback: only one can be registered at a time,
and ``LimaCCDs.py`` already occupies that slot for
``video_last_image`` push events. Frames are only produced while the
main ``LimaCCDs`` device has ``video_live`` set to ``True``, since that
is what drives the camera's video acquisition.

Dependencies
------------

Install these in the same environment as the ``LimaCCDs`` server:

* `aiortc <https://github.com/aiortc/aiortc>`_ — WebRTC stack (H264 encoding, RTP, ICE/DTLS)
* `av <https://github.com/PyAV-Org/PyAV>`_ (PyAV) — pixel format conversion (demosaic, colorspace)
* `Pillow <https://python-pillow.org/>`_ — JPEG/PNG encoding for the snapshot command

If any of these are missing, the device still starts, but ``JoinStream``
and ``SaveLastVideoImage`` raise a Tango exception explaining what to
install.

Supported video modes
----------------------

Raw frames from ``CtVideo`` are converted via ``libswscale`` (through
PyAV), which handles Bayer demosaicing and colorspace conversion in one
step:

.. list-table::
  :header-rows: 1

  * - Lima ``VideoMode``
    - Notes
  * - ``Y8``, ``Y16``
    - Mono
  * - ``RGB24``, ``BGR24``
    -
  * - ``RGB32``, ``BGR32``
    - Treated as packed RGBA/BGRA
  * - ``BAYER_RG8``, ``BAYER_RG16``
    - Demosaiced by libswscale
  * - ``BAYER_BG8``, ``BAYER_BG16``
    - Demosaiced by libswscale

``YUV411/422/444(PACKED)`` modes are not mapped yet — frames in those
modes are dropped with a ``warn_stream`` log line rather than streamed.

For the 16-bit-container modes (``Y16``, ``BAYER_RG16``, ``BAYER_BG16``),
a sensor with a native depth below 16 bits (e.g. a 12-bit Basler sensor)
leaves its raw values unscaled in the low bits of each 16-bit sample,
which renders as near-black. This is detected from the camera's own
``Bpp<N>`` image type and corrected with a left-shift before the frame is
converted or cached for a snapshot — the same fix independently applied
by ``daiquiri``'s ``parse_video_frame()`` and ``video-streamer-mpeg``'s
``CameraBase.frame()``.

Properties
----------

.. list-table::
  :header-rows: 1

  * - Property name
    - Type
    - Default value
    - Description
  * - MaxStreamWidth
    - DevLong
    - 0
    - Downscale streamed frames wider than this (``0`` = no limit). Does not affect ``SaveLastVideoImage``, which always uses the full-size frame.
  * - MaxStreamHeight
    - DevLong
    - 0
    - Downscale streamed frames taller than this (``0`` = no limit). Same exemption as above.
  * - IceServers
    - DevVarStringArray
    - []
    - STUN/TURN server URLs for WebRTC ICE negotiation. Can be left empty when the viewer and server are on the same network segment.
  * - JpegQuality
    - DevShort
    - 90
    - Default JPEG quality (1-100) used by ``SaveLastVideoImage`` when no quality is given.
  * - DisconnectTimeout
    - DevDouble
    - 30.0
    - Seconds a WebRTC connection may stay in the ``disconnected`` state before it is force-closed, in case ``LeaveStream`` is never called (client crash, network drop, ...).
  * - IceHostAddress
    - DevString
    - ""
    - If set, only advertise this IP as a host ICE candidate to viewers, dropping any others (e.g. a Docker bridge interface also present on the server machine).

Commands
--------

.. list-table::
  :header-rows: 1

  * - Command name
    - Arg. in
    - Arg. out
    - Description
  * - Start
    - DevVoid
    - DevVoid
    - Set device state to ON. ``JoinStream`` and ``SaveLastVideoImage`` require the device to be ON.
  * - Stop
    - DevVoid
    - DevVoid
    - Set device state to OFF.
  * - JoinStream
    - DevString — WebRTC SDP offer
    - DevVarStringArray — ``[connection_id, SDP answer]``
    - Starts a new WebRTC viewer session. Media then flows directly between the browser and the server (peer-to-peer over ICE), not through Tango.
  * - LeaveStream
    - DevString — ``connection_id`` from ``JoinStream``
    - DevVoid
    - Closes a viewer's peer connection. Calling this is not required for cleanup to happen — see below — but it releases resources immediately instead of waiting for ``DisconnectTimeout``.
  * - SaveLastVideoImage
    - DevString — ``"JPEG"``, ``"PNG"``, or ``"JPEG:<quality>"`` (e.g. ``"JPEG:75"``)
    - DevVoid
    - Encodes the latest full-size video frame and caches it for the ``last_video_image_snapshot`` attribute. Raises ``NoImage`` if no video frame has been received yet.

Attributes
----------

.. list-table::
  :header-rows: 1

  * - Attribute name
    - rw
    - Type
    - Description
  * - RunLevel
    - rw
    - DevLong
    - Inherited from the base plugin class; not otherwise used by this device.
  * - last_video_image_snapshot
    - ro
    - DevEncoded
    - The JPEG/PNG snapshot produced by ``SaveLastVideoImage``. The encoded byte payload is exactly a standard JPEG or PNG file — write it to disk as-is (e.g. ``snapshot.jpg``) and any image viewer can open it. The ``DevEncoded`` format tag is ``"JPEG"`` or ``"PNG"``, matching whichever was last requested. Reading before calling ``SaveLastVideoImage`` raises ``NoImage``.
  * - last_video_image_snapshot_counter
    - ro
    - DevLong64
    - The frame's own ``frameNumber()`` at the time ``SaveLastVideoImage`` captured it. Use this to detect whether a client already has the latest snapshot without re-reading the image bytes.
  * - stream_max_fps
    - rw
    - DevDouble
    - Caps how often video frames are converted/encoded for WebRTC viewers (``0`` = no cap). Defaults to 24. Frames arriving faster than this from the camera's live mode are dropped before the (relatively expensive) pixel conversion step, not just at the encoder.

Reading the snapshot from a client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

  import tango

  dev = tango.DeviceProxy("id00/limaccds_h264videostream/simulator")
  dev.SaveLastVideoImage("JPEG:90")

  attr = dev.read_attribute("last_video_image_snapshot")
  image_format, data = attr.value  # image_format is "JPEG" or "PNG"

  with open(f"snapshot.{image_format.lower()}", "wb") as f:
      f.write(data)

``SaveLastVideoImage`` and reading the attribute are separate steps: the
command captures and encodes a fresh frame, the attribute just returns
whatever was captured most recently (no re-encoding on read).

WebRTC viewing flow
--------------------

#. Browser creates an ``RTCPeerConnection``, adds a receive-only video
   transceiver, and generates an SDP offer via ``createOffer()`` /
   ``setLocalDescription()``.
#. Some backend that can reach Tango (e.g. the web UI's server) calls
   ``JoinStream(offer_sdp)`` and gets back ``[connection_id, answer_sdp]``.
#. That answer is relayed back to the browser, which calls
   ``setRemoteDescription(answer)``.
#. ICE negotiation and DTLS-SRTP setup happen automatically; video then
   flows directly between the browser and the server.
#. When the viewer disconnects, call ``LeaveStream(connection_id)`` to
   free the peer connection immediately.

In `daiquiri <https://gitlab.esrf.fr/daiquiri/daiquiri>`_, this whole
exchange is exposed as a dedicated ``POST``/``DELETE``
``/imageviewer/sources/webrtc`` pair on the web UI's backend (not gated
by session control, since viewing a stream is read-only), rather than
calling ``JoinStream``/``LeaveStream`` through the generic per-object
hardware-call endpoint.

Cleanup without a clean disconnect
------------------------------------

A client is not guaranteed to call ``LeaveStream`` — the browser tab can
crash, or the network can drop. Cleanup does not depend solely on that
call: it also happens automatically based on the peer connection's own
``connectionstatechange`` events, since WebRTC's ICE/DTLS layer detects a
dead connection on its own.

* ``failed`` or ``closed`` close the connection immediately.
* ``disconnected`` (which can be a brief, recoverable network blip)
  starts a ``DisconnectTimeout``-second grace period; if the connection
  has not recovered to ``connected`` by then, it is force-closed.

``LeaveStream`` and this automatic path share the same cleanup code and
are idempotent with each other — whichever fires first releases the
connection, the other is then a no-op.

Known limitations
------------------

* No explicit H264 bitrate/preset control yet — ``aiortc``'s encoder is
  used with its defaults (``tune=zerolatency``, ``profile=Baseline``,
  ``level=31``, no B-frames; libx264's default ``medium`` preset since
  ``aiortc`` does not set one).
* ``YUV411/422/444(PACKED)`` video modes are not converted.
* Chrome's hardware-accelerated H264 decoder can render a solid black
  picture on some machines (commonly VMs or ones with limited/virtual GPU
  support) despite ``getStats()`` reporting healthy, increasing
  ``framesDecoded`` — a client-side Chrome/GPU-driver issue, not a stream
  problem. Firefox has been observed to render correctly on the same
  machine where this occurs. Disabling
  ``chrome://flags/#disable-accelerated-video-decode`` confirms and works
  around it.
