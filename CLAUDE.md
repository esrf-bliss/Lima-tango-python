# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install in develop mode: `pip install -e .` (requires `lima-core` / `lima.core` bindings and PyTango already available, typically via a conda env such as one of the `lima_*`/`simulator`/`bliss_*` environments under `/opt/bliss/conda/miniconda/envs`)
- Run the test suite: `pytest tests`
- The conda CI recipe (`conda/meta.yaml`) runs `pytest -k "not test_tango" tests` — `test_tango.py` is excluded there because it relies on mocking `PyTango.LatestDeviceImpl.__init__`/`PyTango.Database` directly rather than a real Tango context, and is fragile outside the exact dev setup.
- Run a single test: `pytest tests/test_mask.py::test_mask`
- No linter/formatter config is defined in this repo (no `.flake8`, `pyproject` tool sections, or pre-commit config).

There is no local Tango device server test harness in this repo worth relying on for behavioral regressions. The real integration coverage for `LimaCCDs` + the `Simulator` camera plugin lives in `bliss.git`: `bliss/testutils/controller_utils.py::lima_simulator_context` spawns a real `LimaCCDs` process (via a pixi/conda env, e.g. `LIMA_SIMULATOR_ENV=pixi:lima1` in CI) against a real Tango DB, and ~40+ files under `bliss.git/tests/` (e.g. `controllers_sw/test_lima_simulator.py`, `scans/test_lima_scans.py`) exercise it end-to-end. Treat that suite as the compatibility gate for any change to the Tango-facing interface (attribute/command names, types, semantics).

## Architecture

### This repo in the wider LImA project

This directory (`applications/tango/python`) is one git submodule of the `lima` superproject, which also contains `applications/tango/cpp`, `applications/spec`, `third-party/*`, and ~50 camera-specific submodules under `camera/*` (e.g. `camera/simulator`, `camera/pilatus`, `camera/frelon`...). Each camera submodule ships its own Tango device server plugin under `<camera>/tango/<Name>.py`, built on the same low-level PyTango conventions described below. This package (`lima-tango-server`) provides the generic, camera-agnostic parts: the main `LimaCCDs` device and a set of generic post-processing plugin devices; it does not itself contain any camera-specific code.

### Old-style (low-level) PyTango device pattern

Every device server in this codebase — `lima/server/LimaCCDs.py` and each `lima/server/plugins/*.py` — follows the pre-"high-level-API" PyTango pattern, not `tango.server.Device`/`@attribute`/`@command`:

- A device implementation class subclassing `PyTango.LatestDeviceImpl` (some external camera plugins, e.g. `camera/simulator`, subclass the even older `PyTango.Device_4Impl`).
- A companion `<Name>Class(PyTango.DeviceClass)` declaring `class_property_list`, `device_property_list`, `cmd_list`, and `attr_list` as raw dicts (Tango type/format/access tuples), rather than decorators.
- Per-attribute `read_<Attr>`/`write_<Attr>` methods and `is_<Attr>_allowed` guards, dispatched by Tango via name convention.
- Server bootstrap through `PyTango.Util` (`py.add_TgClass(...)`, `util.add_class(...)`, `U.server_run()`), see `LimaCCDs.main()`.

A rewrite to the modern high-level PyTango API (`tango.server`) is an ongoing, multi-repo effort — see `MIGRATION_ROADMAP.md` for the plan, scope, and phasing.

### `AttrHelper.py`: the generic attribute-to-camera dispatch mechanism

`AttrHelper.get_attr_4u(obj, name, interface)` is a `__getattr__`-based helper that lets a device class avoid writing a `read_X`/`write_X` pair per attribute: it maps `read_foo_bar`/`write_foo_bar` to `interface.getFooBar`/`interface.setFooBar` by naming convention, optionally going through a per-instance enum dict (e.g. `self.__FastTrigger = {"ON": True, "OFF": False}`) when the attribute takes string enum values. This is used pervasively by `lima/server/plugins/*.py` and by essentially every external camera Tango plugin (via `self.__getattr__` delegating to `AttrHelper.get_attr_4u`). **It is a de-facto public contract across the whole camera-plugin ecosystem, not an internal implementation detail** — changing its behavior affects every camera submodule, not just this repo.

### Plugin/camera discovery

`declare_camera_n_commun_to_tango_world()` in `LimaCCDs.py` is called once at server startup and loads:

- Camera modules from `lima.server.camera.__all__` (built by `lima/server/camera/__init__.py` from local `.py` files plus the `Lima_tango_camera` entry-point group — in practice this directory is normally empty here and cameras come from installed camera-plugin packages).
- Generic plugin modules from `lima.server.plugins.__all__` similarly, via the `Lima_tango_plugin` entry-point group (`get_camera_module`/`get_plugin_module` in `EnvHelper.py`).

Each loaded module must expose `get_tango_specific_class_n_device()`, returning either a `(DeviceClass, DeviceImpl)` pair or an object exposing `.TangoClassClass`; the result is registered via `util.add_class(...)`. This function is the extension point every camera/plugin repo must implement — see `MASK.py`/`RoiCounter.py` etc. for the in-repo pattern, and any `camera/<name>/tango/*.py` submodule for the external pattern.

### `EnvHelper.py`

Only part of this module is live: `get_sub_devices`/`get_device_class_map` (queries the real Tango DB for the sibling devices of the running server instance — used throughout `LimaCCDs.py` for config/plugin export and cross-device lookups), `get_lima_camera_type`/`get_lima_device_name`, and `get_camera_module`/`get_plugin_module` (entry-point based dynamic import, described above).

Everything else in the file — `setup_lima_env`, `check_link_strict_version`, `setup_env`, `find_dep_vers`, `set_env_version_depth`, `check_lima_dir`, `version_code`/`version_cmp`, and `to_tango_object`/`__get_ct_classes`/`__filter`/`__to_lower_separator` (a reflection-based adapter turning `Ct*` core objects into Tango-proxy-like objects) — is dead code with no callers anywhere in this repo or in `bliss.git`. `version_cmp` even relies on the Python 2 builtin `cmp()`, so it would raise `NameError` if it were ever reached. Don't build on top of it; it's a removal candidate.

### `EdfFile.py` / `LimaViewer.py`

Self-contained utilities (EDF file format reader/writer, and a standalone Tk-based image viewer script) — not part of the core device-server architecture above.
