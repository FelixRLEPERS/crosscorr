"""Тесты safe_exec.py — песочница исполнения кода (docs/roadmap.md, шаг 4).

Покрываем три слоя защиты:
1. AST-проверку ``_check_forbidden`` — запрещённые имена, атрибуты, импорты;
2. ограничение встроенных функций (SAFE_BUILTINS) внутри ``_worker``;
3. таймаут и завершение процесса в ``run_code_safe``.
"""

import queue as stdlib_queue

import pytest

import crosscorr_lib.safe_exec as safe_exec_module
from crosscorr_lib.safe_exec import (
    FORBIDDEN_NAMES,
    SAFE_BUILTINS,
    _check_forbidden,
    run_code_safe,
)

# Щедрый таймаут: spawn-процесс на Windows стартует ~0.5-2 сек.
GEN_TIMEOUT = 30.0


# --------------------------------------------------------------------------- #
# 1. AST-проверка: запрещённые встроенные функции
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["open", "eval", "exec", "compile", "input"])
def test_check_forbidden_dangerous_builtins(name):
    assert _check_forbidden(f"{name}()") == f"Запрещённое имя: {name}"


@pytest.mark.parametrize("name", ["globals", "locals", "vars", "breakpoint", "memoryview"])
def test_check_forbidden_introspection_builtins(name):
    assert _check_forbidden(f"{name}()") == f"Запрещённое имя: {name}"


def test_check_forbidden_dunder_escape():
    """Dunder-обход через __globals__ блокируется на уровне Attribute."""
    err = _check_forbidden("f.__globals__['x']")
    assert err is not None
    assert err.startswith("Запрещённый атрибут")


# --------------------------------------------------------------------------- #
# 2. AST-проверка: запрещённые импорты
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mod", ["os", "sys", "subprocess", "socket", "pickle", "ctypes"])
def test_check_forbidden_imports(mod):
    assert _check_forbidden(f"import {mod}") == f"Запрещённый импорт: {mod}"


def test_check_forbidden_dotted_import_uses_top_component():
    """import os.path — верхний компонент 'os' запрещён."""
    assert _check_forbidden("import os.path") == "Запрещённый импорт: os.path"


def test_check_forbidden_from_import():
    assert _check_forbidden("from os import system") == "Запрещённый импорт: from os"


def test_check_forbidden_from_importlib():
    assert _check_forbidden("from importlib import import_module") == (
        "Запрещённый импорт: from importlib"
    )


def test_check_forbidden_import_alias_is_still_blocked():
    """import subprocess as sp — алиас не спасает."""
    assert _check_forbidden("import subprocess as sp") == "Запрещённый импорт: subprocess"


# --------------------------------------------------------------------------- #
# 3. AST-проверка: запрещённые атрибуты
# --------------------------------------------------------------------------- #


def test_check_forbidden_attribute():
    assert _check_forbidden("f.open('r')") == "Запрещённый атрибут: open"


def test_check_forbidden_dunder_attribute_chain():
    err = _check_forbidden("().__class__.__mro__")
    assert err is not None
    assert err.startswith("Запрещённый атрибут")


def test_check_forbidden_name_requests_without_import():
    """Неимпортированный requests — это Name, и он тоже запрещён."""
    assert _check_forbidden("requests.get('http://x')") == "Запрещённое имя: requests"


# --------------------------------------------------------------------------- #
# 4. AST-проверка: разрешённый код и синтаксические ошибки
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "code",
    [
        "import numpy as np",
        "from math import sqrt",
        "print(len('abc'))",
        "x = [i * 2 for i in range(10)]",
        "result = sorted([3, 1, 2])",
        "data = {'a': 1, 'b': 2}",
    ],
)
def test_check_forbidden_allows_safe_code(code):
    assert _check_forbidden(code) is None


def test_check_forbidden_syntax_error():
    err = _check_forbidden("def foo(:")
    assert err is not None
    assert err.startswith("Синтаксическая ошибка")
    assert "строка 1" in err


def test_forbidden_names_and_builtins_are_consistent():
    """SAFE_BUILTINS не должен содержать ни одного запрещённого имени."""
    assert not (SAFE_BUILTINS.keys() & FORBIDDEN_NAMES)


# --------------------------------------------------------------------------- #
# 5. run_code_safe: исполнение в дочернем процессе
# --------------------------------------------------------------------------- #


def test_run_code_safe_captures_stdout():
    out, err = run_code_safe("print('hello sandbox')", timeout=GEN_TIMEOUT)
    assert err is None
    assert out == "hello sandbox\n"


def test_run_code_safe_blocks_import_before_spawn():
    """Опасный импорт отсекается AST-проверкой до старта процесса."""
    out, err = run_code_safe("import os; print(os.getcwd())", timeout=GEN_TIMEOUT)
    assert out == ""
    assert err == "Запрещённый импорт: os"


def test_run_code_safe_blocks_forbidden_name():
    out, err = run_code_safe("data = open('x.txt')", timeout=GEN_TIMEOUT)
    assert out == ""
    assert err == "Запрещённое имя: open"


def test_run_code_safe_reports_runtime_error():
    """Исключение внутри кода возвращается как 'Тип: сообщение'."""
    out, err = run_code_safe("print(undefined_name)", timeout=GEN_TIMEOUT)
    assert out == ""
    assert err == "NameError: name 'undefined_name' is not defined"


def test_run_code_safe_enforces_builtins_whitelist():
    """hash() есть в реальных builtins, но нет в SAFE_BUILTINS -> NameError."""
    out, err = run_code_safe("print(hash('a'))", timeout=GEN_TIMEOUT)
    assert out == ""
    assert "NameError" in err


def test_run_code_safe_multiline_output():
    out, err = run_code_safe("for i in range(3):\n    print(i)", timeout=GEN_TIMEOUT)
    assert err is None
    assert out == "0\n1\n2\n"


def test_run_code_safe_empty_code():
    out, err = run_code_safe("", timeout=GEN_TIMEOUT)
    assert err is None
    assert out == ""


def test_run_code_safe_timeout_terminates_worker():
    """Бесконечный цикл обрывается по timeout, а не висит вечно."""
    out, err = run_code_safe("while True:\n    pass", timeout=1.0)
    assert out == ""
    assert err is not None
    assert "Превышено время выполнения" in err
    assert "1.0" in err


def test_run_code_safe_system_exit_name_is_whitelisted_out():
    """SystemExit нет в SAFE_BUILTINS -> NameError ещё до raise.

    Ограничение встроенных функций не даёт поднять BaseException, поэтому
    ветка «ребёнок завершился без результата» проверяется отдельно ниже.
    """
    out, err = run_code_safe("raise SystemExit(1)", timeout=GEN_TIMEOUT)
    assert out == ""
    assert err == "NameError: name 'SystemExit' is not defined"


def test_run_code_safe_empty_queue_returns_message(monkeypatch):
    """Ветка «Процесс завершился без результата»: очередь пуста после join.

    Симулируем процесс, который завершился, ничего не положив в очередь
    (такой исход на практике трудно воспроизвести без убийства spawn-потока).
    """

    class _EmptyQueue:
        def get_nowait(self):
            raise Exception("очередь пуста")

    class _NoopProcess:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def join(self, timeout=None):
            pass

        def is_alive(self):
            return False

    class _FakeContext:
        def Queue(self):
            return _EmptyQueue()

        def Process(self, *args, **kwargs):
            return _NoopProcess()

    class _FakeMp:
        @staticmethod
        def get_context(name):
            return _FakeContext()

    monkeypatch.setattr(safe_exec_module, "mp", _FakeMp())

    out, err = run_code_safe("print('не выполнится')")
    assert out == ""
    assert err == "Процесс завершился без результата"


def test_worker_reports_ok_and_error_in_process():
    """_worker выполняется в дочернем процессе (coverage там не пишется).

    Вызываем его напрямую, чтобы проверить обе ветки результата: перехват
    stdout при успехе и «Тип: сообщение» при исключении.
    """
    q_ok = stdlib_queue.Queue()
    safe_exec_module._worker("print('hi'); print('there')", q_ok)
    status, payload = q_ok.get_nowait()
    assert status == "ok"
    assert payload == "hi\nthere\n"

    q_err = stdlib_queue.Queue()
    safe_exec_module._worker("1 / 0", q_err)
    status, payload = q_err.get_nowait()
    assert status == "error"
    assert payload.startswith("ZeroDivisionError:")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
