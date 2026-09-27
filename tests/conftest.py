"""Windows compatibility for the installed gltest direct-mode SDK."""
import os
import sys
from pathlib import Path

import pytest


_held = []
_unlink = os.unlink


@pytest.fixture(autouse=True)
def windows_gltest_runtime(monkeypatch):
    if os.name != "nt":
        return
    import gltest.direct.loader as loader
    import gltest.direct.vm as vm_module

    original_inject = loader._inject_message_to_fd0
    original_warp = vm_module.VMContext.warp

    def inject(vm):
        def deferred_unlink(path, *args, **kwargs):
            try:
                return _unlink(path, *args, **kwargs)
            except PermissionError as error:
                if error.winerror != 32 or not Path(path).name.startswith("tmp"):
                    raise
                _held.append(path)
        with monkeypatch.context() as local:
            local.setattr(os, "unlink", deferred_unlink)
            original_inject(vm)

    def warp(vm, timestamp):
        original_warp(vm, timestamp)
        message = sys.modules.get("genlayer.message")
        if message is not None:
            raw = getattr(message, "raw", None)
            if isinstance(raw, dict):
                raw["datetime"] = timestamp
            setattr(message, "datetime", timestamp)

    monkeypatch.setattr(loader, "_inject_message_to_fd0", inject)
    monkeypatch.setattr(vm_module.VMContext, "warp", warp)
