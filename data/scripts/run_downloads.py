"""
Мастер-скрипт для последовательной загрузки и унификации данных из всех внешних источников.

ВНИМАНИЕ: Этот скрипт является оркестратором. Он не содержит логики парсинга, 
а только вызывает функции скачивания и контролирует их выполнение.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

# Импортируем все модули загрузки. Это должно работать, так как они находятся в одном пакете.
try:
    from .download_wspr import fetch_wspr # Используем функцию из основного скрипта
    from .download_intermagnet import download_and_save_intermagnet 
    # Предполагаем, что для Horizons и другие модули будут реализованы аналогичные функции-обёртки.
    
except ImportError as e:
    print(f"ОШИБКА ИМПОРТА: Убедитесь, что все скрипты загрузки (wspr, intermagnet и т.д.) существуют в папке data/scripts/")
    # Если импорт не удался, то дальнейшая работа будет прервана.


def run_full_download(target_date: dt.date, intermag_station: str, horizon_start: dt.date, horizon_end: dt.date) -> dict:
    """
    Выполняет последовательный запуск всех загрузчиков данных.
    Возвращает словарь с отчётом по статусу каждого источника.
    """
    print("\n===============================================")
    print("🚀 СТАРТ ПОЛНОГО ЦИКЛА ЗАГРУЗКИ ДАННЫХ 🚀")
    print(f"Цель: {target_date} | Обсерватория: {intermag_station}")
    print("===============================================")

    results = {}
    
    # --- БЛОК 1: WSPR (Загрузка) ---
    print("\n--- Запуск загрузки WSPR ---")
    try:
        # Используем функцию fetch_wspr из modules/download_wspr.py
        df_wspr = fetch_wspr(target_date, band="20m", limit=5000) 
        results['WSPR'] = {"status": "SUCCESS", "data_points": len(df_wspr)}
    except Exception as e:
        print(f"[ОШИБКА] Не удалось загрузить WSPR: {e}")
        results['WSPR'] = {"status": "FAILED", "error": str(e)}

    # --- БЛОК 2: INTERMAGNET (Загрузка) ---
    print("\n--- Запуск загрузки INTERMAGNET ---")
    try:
        download_and_save_intermagnet(intermag_station, target_date.year, target_date.month)
        results['INTERMAGNET'] = {"status": "SUCCESS", "message": f"Данные сохранены для {intermag_station}."}
    except Exception as e:
        print(f"[ОШИБКА] Не удалось загрузить INTERMAGNET: {e}")
        results['INTERMAGNET'] = {"status": "FAILED", "error": str(e)}

    # --- БЛОК 3: HORIZONS (Загрузка) ---
    print("\n--- Запуск загрузки JPL Horizons ---")
    try:
        # Здесь будет вызов функции для Horizon, которая должна быть реализована
        results['HORIZONS'] = {"status": "SKIPPED", "note": "Функция download_horizons.py еще не импортирована."}
    except Exception as e:
        print(f"[ОШИБКА] Не удалось загрузить JPL Horizons: {e}")
        results['HORIZONS'] = {"status": "FAILED", "error": str(e)}

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Мастер-скрипт для загрузки всех данных CrossCorr.")
    parser.add_argument("--date", required=True, help="Целевая дата (YYYY-MM-DD) для WSPR и других скриптов.")
    parser.add_argument("--station", required=True, help="Код станции INTERMAGNET (например, MOS).")

    args = parser.parse_args()
    try:
        target_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        print("Ошибка: Неверный формат даты. Используйте YYYY-MM-DD.")
        return

    # Запуск основного цикла
    report = run_full_download(target_date, args.station, target_date, target_date)

    print("\n===============================================")
    print("✅ СТАТУС ЗАГРУЗКИ: АНАЛИТИЧЕСКИЙ ОТЧЁТ")
    print("-----------------------------------------------")
    for source, result in report.items():
        status = "✅ УСПЕШНО" if result['status'] == "SUCCESS" else ("⚠️ ОШИБКА" if result['status'] == "FAILED" else "⏸️ ПРОПУЩЕНО")
        print(f"[{source: <12}] {status}")
    print("===============================================")


if __name__ == "__main__":
    # При запуске скрипта напрямую, он ожидает аргументы из командной строки.
    # В режиме отладки (для тестирования) можно передать заглушки.
    main()