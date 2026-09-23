"""Безопасное выполнение кода с timeout и ограничениями.

Использует multiprocessing со spawn-контекстом (Windows-совместимый).
Запрет опасных имён — через AST-парсер (не наивный substring).
"""

from __future__ import annotations

import ast
import io
import contextlib
import multiprocessing as mp


# Запрещённые имена модулей/функций (проверяются через AST)
FORBIDDEN_NAMES = {
    # Опасные встроенные функции
    "open", "exec", "eval", "compile",
    "__import__", "input", "exit", "quit",
    "globals", "locals", "vars",
    "breakpoint", "memoryview",
    # Опасные модули
    "os", "sys", "subprocess", "shutil",
    "socket", "requests", "urllib", "http",
    "pathlib", "tempfile", "pickle", "shelve",
    # Dunder-обходы (НЕ ДАВАТЬ вырваться из песочницы)
    "__class__", "__base__", "__subclasses__",
    "__bases__", "__mro__", "__globals__",
    "__builtins__", "__dict__", "__getattribute__",
    "__getattr__", "__setattr__", "__delattr__",
    "__reduce__", "__reduce_ex__",
    "importlib",
}


# Разрешённые встроенные функции
SAFE_BUILTINS = {
    "print": print, "len": len, "range": range,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "str": str, "int": int, "float": float, "bool": bool,
    "sum": sum, "min": min, "max": max, "abs": abs,
    "round": round, "sorted": sorted, "reversed": reversed,
    "enumerate": enumerate, "zip": zip, "map": map,
    "filter": filter, "any": any, "all": all,
    "isinstance": isinstance, "type": type,
    "True": True, "False": False, "None": None,
}


def _check_forbidden(code_str: str) -> str | None:
    """
    Проверяет код через AST на запрещённые имена.

    Возвращает None если всё OK, иначе — сообщение об ошибке.
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return f"Синтаксическая ошибка: {e.msg} (строка {e.lineno})"

    for node in ast.walk(tree):
        # Запрещённые имена: foo(...)
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return f"Запрещённое имя: {node.id}"

        # Запрещённые атрибуты: obj.open(...)
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
            return f"Запрещённый атрибут: {node.attr}"

        # Запрещённые импорты: import os
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_NAMES:
                    return f"Запрещённый импорт: {alias.name}"

        # Запрещённые импорты: from os import system
        if isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in FORBIDDEN_NAMES:
                    return f"Запрещённый импорт: from {node.module}"

    return None


def _worker(code: str, result_queue: mp.Queue) -> None:
    """Выполняется в дочернем процессе. Не имеет доступа к Streamlit."""
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(code, {"__builtins__": SAFE_BUILTINS}, {})
        result_queue.put(("ok", output.getvalue()))
    except Exception as e:
        result_queue.put(("error", f"{type(e).__name__}: {e}"))


def run_code_safe(code: str, timeout: float = 5.0) -> tuple[str, str | None]:
    """
    Выполняет код в отдельном процессе с timeout.

    Возвращает:
        (output, error) — output: stdout, error: str или None.
    """
    # AST-проверка на запрещённые имена
    error = _check_forbidden(code)
    if error:
        return "", error

    # Используем spawn-контекст (Windows-совместимый)
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_worker, args=(code, queue), daemon=True)

    proc.start()
    proc.join(timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join(1.0)
        if proc.is_alive():
            proc.kill()
        return "", f"Превышено время выполнения ({timeout} сек)"

    try:
        status, payload = queue.get_nowait()
    except Exception:
        return "", "Процесс завершился без результата"

    if status == "ok":
        return payload, None
    return "", payload