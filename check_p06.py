"""Проверка P0-6 / P2-2: safe exec с AST-парсером."""

from crosscorr_lib.safe_exec import run_code_safe


def test_simple_code():
    out, err = run_code_safe("print('hello')")
    assert err is None, f"Ошибка: {err}"
    assert "hello" in out
    print("✓ Простой код работает")


def test_infinite_loop():
    out, err = run_code_safe("while True: pass", timeout=2.0)
    assert err is not None
    assert "Превышено" in err
    print(f"✓ Бесконечный цикл прерван: {err}")


def test_long_loop():
    code = """
total = 0
for i in range(10**10):
    total = total + i
print(total)
"""
    out, err = run_code_safe(code, timeout=3.0)
    assert err is not None
    assert "Превышено" in err
    print(f"✓ Долгий цикл прерван: {err}")


def test_forbidden_open():
    out, err = run_code_safe("f = open('file.txt')")
    assert err is not None
    assert "Запрещённое" in err
    print(f"✓ open заблокирован: {err}")


def test_forbidden_import():
    out, err = run_code_safe("import os\nprint(os.getcwd())")
    assert err is not None
    assert "Запрещённый импорт" in err
    print(f"✓ import os заблокирован: {err}")


def test_false_positive_position():
    """pos содержит 'os' — раньше ложно блокировалось."""
    out, err = run_code_safe("pos = 5\nprint(pos)")
    assert err is None, f"Ложное срабатывание: {err}"
    assert "5" in out
    print("✓ 'pos' (содержит 'os') НЕ блокируется")


def test_false_positive_closed():
    """close содержит 'os' — раньше ложно блокировалось."""
    out, err = run_code_safe("closed = True\nprint(closed)")
    assert err is None, f"Ложное срабатывание: {err}"
    print("✓ 'closed' (содержит 'os') НЕ блокируется")


def test_false_positive_most():
    """most содержит 'os' — раньше ложно блокировалось."""
    out, err = run_code_safe("most = 100\nprint(most)")
    assert err is None, f"Ложное срабатывание: {err}"
    print("✓ 'most' (содержит 'os') НЕ блокируется")


def test_syntax_error():
    """Синтаксическая ошибка — нормальное сообщение."""
    out, err = run_code_safe("if True\n    print('hi')")
    assert err is not None
    assert "Синтаксическая" in err
    print(f"✓ Синтаксическая ошибка: {err}")


def test_normal_loop():
    code = """
total = 0
for i in range(10):
    total = total + i
print("Сумма:", total)
"""
    out, err = run_code_safe(code)
    assert err is None
    assert "Сумма: 45" in out
    print("✓ Нормальный цикл работает")


if __name__ == "__main__":
    test_simple_code()
    test_infinite_loop()
    test_long_loop()
    test_forbidden_open()
    test_forbidden_import()
    test_false_positive_position()
    test_false_positive_closed()
    test_false_positive_most()
    test_syntax_error()
    test_normal_loop()
    print()
    print("OK — все проверки P0-6 + P2-2 прошли")