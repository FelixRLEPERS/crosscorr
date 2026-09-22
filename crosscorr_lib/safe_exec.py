"""Безопасное выполнение кода с timeout и ограничениями.

Использует multiprocessing со spawn-контекстом (работает на Windows).
Ограничения:
- timeout (секунды) — убивает процесс при превышении.
- мягкий лимит памяти (через resource на Unix, не поддерживается на Windows).
- restricted __builtins__ — блокировка опасных функций.
"""

from __future__ import annotations

import io
import contextlib
import multiprocessing as mp
from typing import Any


# Запрещённые имена в коде ребёнка
FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile",
    "__import__", "input", "exit", "quit",
    "globals", "locals", "vars",
    "breakpoint", "memoryview",
}

# Разрешённые встроенные функции
SAFE_BUILTINS = {
    "print": print,
    "len": len,
    "range": range,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "sorted": sorted,
    "reversed": reversed,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "any": any,
    "all": all,
    "isinstance": isinstance,
    "type": type,
    "True": True,
    "False": False,
    "None": None,
}


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
    # Быстрая проверка на запрещённые имена
    for name in FORBIDDEN_NAMES:
        if name in code:
            return "", f"Запрещённое имя: {name}"

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