"""Проверка P0-6: timeout и безопасность exec."""

from crosscorr_lib.safe_exec import run_code_safe


def test_simple_code():
    out, err = run_code_safe("print('hello')")
    assert err is None, f"Ошибка: {err}"
    assert "hello" in out, f"Нет 'hello': {out}"
    print("✓ Простой код работает")


def test_infinite_loop():
    out, err = run_code_safe("while True: pass", timeout=2.0)
    assert err is not None, "Timeout не сработал"
    assert "Превышено" in err, f"Неверная ошибка: {err}"
    print(f"✓ Бесконечный цикл прерван: {err}")


def test_memory_bomb():
    """Долгий цикл вычислений — должен упасть по timeout."""
    # 10 миллиардов итераций — точно не уложится в 3 секунды
    code = """
total = 0
for i in range(10**10):
    total = total + i
print(total)
"""
    out, err = run_code_safe(code, timeout=3.0)
    assert err is not None, "Timeout не сработал на долгом цикле"
    assert "Превышено" in err, f"Неверная ошибка: {err}"
    print(f"✓ Долгий цикл прерван: {err}")


def test_forbidden_name():
    out, err = run_code_safe("open('file.txt')")
    assert err is not None, "Запрещённое имя не сработало"
    assert "Запрещённое" in err, f"Неверная ошибка: {err}"
    print(f"✓ Запрещённое имя заблокировано: {err}")


def test_loop_with_output():
    code = """
total = 0
for i in range(10):
    total = total + i
print("Сумма:", total)
"""
    out, err = run_code_safe(code)
    assert err is None, f"Ошибка: {err}"
    assert "Сумма: 45" in out, f"Неверно: {out}"
    print("✓ Нормальный цикл работает")


if __name__ == "__main__":
    test_simple_code()
    test_infinite_loop()
    test_memory_bomb()
    test_forbidden_name()
    test_loop_with_output()
    print()
    print("OK — все проверки P0-6 прошли")