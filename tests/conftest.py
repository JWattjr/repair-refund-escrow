"""Windows and legacy-SDK compatibility for the installed gltest direct runner."""
import importlib
import io
import os
import sys
from pathlib import Path
import pytest


_held = []
_unlink = os.unlink
_fileio = io.FileIO


class _InjectedMessage:
    def __init__(self, payload):
        self.payload = payload

    def readall(self):
        return self.payload


def _sync_legacy_message(vm):
    legacy = sys.modules.get("genlayer.gl")
    if legacy is None or not hasattr(legacy, "MessageType"):
        return

    Address = legacy.Address
    u256 = legacy.u256

    def address(value):
        if value is None or isinstance(value, Address):
            return value
        if isinstance(value, (bytes, bytearray)):
            return Address(bytes(value))
        if hasattr(value, "as_bytes"):
            return Address(value.as_bytes)
        return Address(value)

    contract_address = address(vm._contract_address)
    sender_address = address(vm.sender)
    origin_address = address(vm.origin)
    raw = legacy.message_raw
    raw.update(
        {
            "contract_address": contract_address,
            "sender_address": sender_address,
            "origin_address": origin_address,
            "value": u256(vm._value),
            "chain_id": u256(vm._chain_id),
            "datetime": vm._datetime,
        }
    )
    legacy.message = legacy.MessageType(
        contract_address=contract_address,
        sender_address=sender_address,
        origin_address=origin_address,
        value=u256(vm._value),
        chain_id=u256(vm._chain_id),
    )


@pytest.fixture(autouse=True)
def windows_gltest_runtime(monkeypatch):
    if os.name != "nt":
        return

    import gltest.direct.loader as loader
    import gltest.direct.vm as vm_module
    from gltest.direct import wasi_mock

    original_inject = loader._inject_message_to_fd0
    original_allocate = loader._allocate_contract
    original_load = loader._load_module
    original_warp = vm_module.VMContext.warp
    original_refresh = vm_module.VMContext._refresh_gl_message
    original_run_validator = vm_module.VMContext.run_validator
    original_patch_nondet = loader._patch_run_nondet_for_direct_mode
    original_import_calldata = loader.import_calldata
    original_import_address = loader.import_address
    message_payloads = []
    current_vm = [None]

    def import_calldata():
        try:
            return original_import_calldata()
        except ImportError:
            return importlib.import_module("genlayer.py.calldata")

    def import_address():
        try:
            return original_import_address()
        except ImportError:
            return importlib.import_module("genlayer.py.types").Address

    def inject(vm):
        current_vm[0] = vm
        calldata = loader.import_calldata()
        original_encode = calldata.encode

        def capture(payload):
            encoded = original_encode(payload)
            if isinstance(payload, dict) and "entry_kind" in payload and "contract_address" in payload:
                message_payloads.append(encoded)
            return encoded

        def deferred_unlink(path, *args, **kwargs):
            try:
                return _unlink(path, *args, **kwargs)
            except PermissionError as error:
                if error.winerror != 32 or not Path(path).name.startswith("tmp"):
                    raise
                _held.append(path)

        with monkeypatch.context() as local:
            local.setattr(calldata, "encode", capture)
            local.setattr(os, "unlink", deferred_unlink)
            original_inject(vm)

    def allocate_contract(contract_cls, vm, *args, **kwargs):
        if not getattr(contract_cls, "__gl_contract__", False):
            return original_allocate(contract_cls, vm, *args, **kwargs)

        from genlayer.py.storage import ROOT_SLOT_ID
        from genlayer.py.storage._internal.generate import (
            ORIGINAL_INIT_ATTR,
            Lit,
            _storage_build,
        )

        description = _storage_build(contract_cls, {})
        if isinstance(description, Lit):
            return original_allocate(contract_cls, vm, *args, **kwargs)
        slot = vm._storage.get_store_slot(ROOT_SLOT_ID)
        instance = description.get(slot, 0)
        init = getattr(description, "cls", None)
        if init is None:
            init = getattr(contract_cls, "__init__", None)
        else:
            init = getattr(init, "__init__", None)
        if init is not None:
            if hasattr(init, ORIGINAL_INIT_ATTR):
                init = getattr(init, ORIGINAL_INIT_ATTR)
            init(instance, *args, **kwargs)
        return loader._make_contract_proxy(instance)
    def load_module(path):
        if not message_payloads:
            return original_load(path)

        payload = message_payloads[-1]

        def fileio(file, *args, **kwargs):
            if file == 0:
                return _InjectedMessage(payload)
            return _fileio(file, *args, **kwargs)

        with monkeypatch.context() as local:
            local.setattr(io, "FileIO", fileio)
            module = original_load(path)

        if current_vm[0] is not None:
            _sync_legacy_message(current_vm[0])
        return module

    def run_validator(vm, *, leader_result=vm_module._sentinel, leader_error=None, index=-1):
        if "genlayer.gl" not in sys.modules:
            return original_run_validator(
                vm, leader_result=leader_result, leader_error=leader_error, index=index
            )

        from genlayer.gl import vm as legacy_vm

        if not vm._captured_validators:
            raise RuntimeError("No validator captured for this legacy contract")
        stored_result, leader_fn, validator_fn = vm._captured_validators[index]
        if leader_error is not None:
            wrapped = legacy_vm.UserError(str(leader_error))
        elif leader_result is not vm_module._sentinel:
            wrapped = legacy_vm.Return(calldata=leader_result)
        else:
            wrapped = legacy_vm.Return(calldata=stored_result)
        return validator_fn(wrapped)
    def refresh(vm):
        original_refresh(vm)
        _sync_legacy_message(vm)

    def warp(vm, timestamp):
        original_warp(vm, timestamp)
        message = sys.modules.get("genlayer.message")
        if message is not None:
            raw = getattr(message, "raw", None)
            if isinstance(raw, dict):
                raw["datetime"] = timestamp
            setattr(message, "datetime", timestamp)
        _sync_legacy_message(vm)

    def patch_nondet():
        original_patch_nondet()
        try:
            from genlayer.gl import vm as legacy_vm
            from gltest.direct import wasi_mock
        except ImportError:
            return

        def direct_run_nondet(leader_fn, validator_fn, /, **kwargs):
            vm = wasi_mock.get_vm()
            if vm._check_pickling:
                loader._validate_pickling(leader_fn, "leader_fn")
                loader._validate_pickling(validator_fn, "validator_fn")
            vm._in_nondet = True
            try:
                result = leader_fn()
            finally:
                vm._in_nondet = False
            vm._captured_validators.append((result, leader_fn, validator_fn))
            return result

        legacy_vm.run_nondet_unsafe = direct_run_nondet

    monkeypatch.setattr(loader, "import_calldata", import_calldata)
    monkeypatch.setattr(wasi_mock, "import_calldata", import_calldata)
    monkeypatch.setattr(loader, "import_address", import_address)
    monkeypatch.setattr(loader, "_inject_message_to_fd0", inject)
    monkeypatch.setattr(loader, "_allocate_contract", allocate_contract)
    monkeypatch.setattr(loader, "_load_module", load_module)
    monkeypatch.setattr(loader, "_patch_run_nondet_for_direct_mode", patch_nondet)
    monkeypatch.setattr(vm_module.VMContext, "_refresh_gl_message", refresh)
    monkeypatch.setattr(vm_module.VMContext, "run_validator", run_validator)
    monkeypatch.setattr(vm_module.VMContext, "warp", warp)