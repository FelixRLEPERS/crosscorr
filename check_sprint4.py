"""Проверка Sprint 4.2: AST-блокировка dunder-обходов."""

from crosscorr_lib.safe_exec import run_code_safe


def main():
    # 1. Позитивный тест — обычный код
    out, err = run_code_safe("x = 5\nprint(x)")
    assert err is None, f"Ошибка: {err}"
    assert "5" in out
    print("✓ Обычный код работает")

    # 2. Ложные позитивы — не должны блокироваться
    out, err = run_code_safe("position = 10\nprint(position)")
    assert err is None, f"Ложное срабатывание: {err}"
    print("✓ 'position' не блокируется")

    out, err = run_code_safe("closed = True\nprint(closed)")
    assert err is None, f"Ложное срабатывание: {err}"
    print("✓ 'closed' не блокируется")

    # 3. Реальные обходы — должны блокироваться
    malicious = [
        "x = ().__class__.__base__.__subclasses__()",
        "x = ().__class__.__bases__",
        "x = ().__class__.__mro__",
        "x = (lambda: 0).__globals__",
        "import importlib",
    ]
    for code in malicious:
        out, err = run_code_safe(code)
        assert err is not None, f"НЕ заблокировано: {code}"
        assert "Запрещ" in err, f"Неверная ошибка для {code}: {err}"
        print(f"✓ Заблокировано: {code[:45]}...")

    print("\nOK — Sprint 4.2 пройден")


if __name__ == "__main__":
    main()