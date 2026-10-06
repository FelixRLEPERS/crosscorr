"""Behavioral cleanup checks adapted from Qwen's Windows CI scenarios."""

import subprocess
import sys
from multiprocessing import shared_memory

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib import pairs

_SharedMemory = shared_memory.SharedMemory


@pytest.fixture
def wide_data():
    return pd.DataFrame(
        np.random.default_rng(42).standard_normal((200, 4)),
        columns=["a", "b", "c", "d"],
    )


@pytest.fixture
def tracked_shm(monkeypatch):
    """Track real owner and worker handles without retaining buffer views."""
    original = shared_memory.SharedMemory
    handles = []

    def tracked(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append((handle, kwargs.get("create", False)))
        return handle

    monkeypatch.setattr(pairs.shm_module, "SharedMemory", tracked)
    yield handles
    # Clean up even when an assertion detects a real leak.
    for handle, owner in handles:
        try:
            handle.close()
        finally:
            if owner:
                try:
                    handle.unlink()
                except FileNotFoundError:
                    pass


def _assert_released(handles):
    assert handles, "No shared memory allocated; cleanup was not exercised"
    for handle, owner in handles:
        assert handle.buf is None, f"Handle still open: {handle.name}"
        if owner:
            try:
                attached = _SharedMemory(name=handle.name)
            except FileNotFoundError:
                continue
            attached.close()
            pytest.fail(f"Shared memory still accessible: {handle.name}")


def test_no_leak_after_normal_run(wide_data, tracked_shm):
    first = pairs.cross_correlation_pairs_with_max_stat(
        wide_data, B=10, seed=42, n_jobs=2,
    )
    _assert_released(tracked_shm)
    second = pairs.cross_correlation_pairs_with_max_stat(
        wide_data, B=10, seed=42, n_jobs=2,
    )
    pd.testing.assert_frame_equal(first, second)
    assert sum(owner for _, owner in tracked_shm) == 4
    _assert_released(tracked_shm)


def test_no_leak_after_exception(wide_data, tracked_shm, monkeypatch):
    """Exercise failures after allocation, including the second attachment."""
    original_constructor = pairs.shm_module.SharedMemory
    original_batch = pairs._batch_max_stat_corr
    original_surrogates = pairs._make_surrogates

    def fail(*args, **kwargs):
        raise RuntimeError("injected failure")

    def fail_second_owner(*args, **kwargs):
        if kwargs.get("create") and kwargs.get("size") == wide_data.values.nbytes:
            raise RuntimeError("injected failure")
        return original_constructor(*args, **kwargs)

    def fail_worker_attachment(*args, **kwargs):
        if not kwargs.get("create", False):
            owners = [handle for handle, owner in tracked_shm if owner]
            if kwargs.get("name") == owners[-1].name:
                raise RuntimeError("injected failure")
        return original_constructor(*args, **kwargs)

    for constructor, batch, surrogates in [
        (original_constructor, original_batch, fail),
        (fail_second_owner, original_batch, original_surrogates),
        (fail_worker_attachment, original_batch, original_surrogates),
        (original_constructor, fail, original_surrogates),
    ]:
        monkeypatch.setattr(pairs.shm_module, "SharedMemory", constructor)
        monkeypatch.setattr(pairs, "_batch_max_stat_corr", batch)
        monkeypatch.setattr(pairs, "_make_surrogates", surrogates)
        with pytest.raises(RuntimeError, match="injected failure"):
            pairs.cross_correlation_pairs_with_max_stat(wide_data, B=10, n_jobs=1)
        _assert_released(tracked_shm)

    monkeypatch.setattr(pairs.shm_module, "SharedMemory", original_constructor)
    monkeypatch.setattr(pairs, "_batch_max_stat_corr", original_batch)
    monkeypatch.setattr(pairs, "_make_surrogates", original_surrogates)
    original_worker = pairs._worker
    monkeypatch.setattr(pairs, "_worker", fail)
    with pytest.raises(RuntimeError, match="injected failure"):
        pairs.cross_correlation_pairs_with_max_stat(wide_data, B=10, n_jobs=2)
    _assert_released(tracked_shm)
    monkeypatch.setattr(pairs, "_worker", original_worker)
    assert len(pairs.cross_correlation_pairs_with_max_stat(wide_data, B=10, n_jobs=2)) == 6
    _assert_released(tracked_shm)


def test_explicit_unlink_in_finally(wide_data, tracked_shm, monkeypatch):
    """Unlink runs after a close error; a missing segment is harmless."""
    original_close = _SharedMemory.close
    original_unlink = _SharedMemory.unlink
    events = []

    def close_then_fail(handle):
        events.append((handle.name, "close"))
        original_close(handle)
        raise RuntimeError("close failed")

    def unlink_then_missing(handle):
        events.append((handle.name, "unlink"))
        original_unlink(handle)
        raise FileNotFoundError(handle.name)

    handle = pairs.shm_module.SharedMemory(create=True, size=32)
    with monkeypatch.context() as patch:
        patch.setattr(_SharedMemory, "close", close_then_fail)
        patch.setattr(_SharedMemory, "unlink", unlink_then_missing)
        with pytest.raises(RuntimeError, match="close failed"):
            pairs._close_and_unlink(handle)
    assert events == [(handle.name, "close"), (handle.name, "unlink")]
    _assert_released(tracked_shm)

    # A missing unlink must also be tolerated by the public pipeline.
    with monkeypatch.context() as patch:
        patch.setattr(_SharedMemory, "unlink", unlink_then_missing)
        assert len(pairs.cross_correlation_pairs_with_max_stat(wide_data, B=5, n_jobs=1)) == 6
    _assert_released(tracked_shm)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific")
def test_windows_no_resource_tracker_warning():
    """Capture warnings from workers and resource trackers through shutdown."""
    script = """
import numpy as np
import pandas as pd
from joblib.externals.loky import get_reusable_executor
from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat

if __name__ == '__main__':
    for n in (100, 200, 300):
        wide = pd.DataFrame(np.random.default_rng(n).normal(size=(n, 4)))
        result = cross_correlation_pairs_with_max_stat(wide, B=10, n_jobs=2)
        assert len(result) == 6
    get_reusable_executor().shutdown(wait=True)
"""
    result = subprocess.run(
        [sys.executable, "-W", "always", "-c", script],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    stderr = result.stderr.lower()
    assert "resource_tracker" not in stderr, result.stderr
    assert "leaked" not in stderr, result.stderr
    assert "buffererror" not in stderr, result.stderr


def test_sequential_calls_different_sizes(tracked_shm):
    for n in (100, 200, 300):
        wide = pd.DataFrame(
            np.random.default_rng(n).standard_normal((n, 3)),
            columns=["a", "b", "c"],
        )
        result = pairs.cross_correlation_pairs_with_max_stat(wide, B=5, seed=42, n_jobs=2)
        assert len(result) == 3
        _assert_released(tracked_shm)
    names = [handle.name for handle, owner in tracked_shm if owner]
    assert len(names) == len(set(names)) == 6
