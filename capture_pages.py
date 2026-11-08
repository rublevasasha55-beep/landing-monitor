"""Делает реальные PNG-скриншоты страниц локального Streamlit-приложения.

Запуск: python capture_pages.py
Зависимости: pip install -r requirements.txt && python -m playwright install chromium
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "report" / "screenshots"
PAGES = [
    ("overview", "01_obzor", "Рекламные страницы под контролем"),
    ("landings", "02_lendingi", "Лендинги и кампании"),
    ("check", "03_proverka_url", "Проверка URL"),
    ("incidents", "04_incidenty", "Инциденты"),
    ("risks", "05_biznes_riski", "Бизнес-риски рекламных кампаний"),
]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_ready(base: str, process: subprocess.Popen, timeout: int = 75) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Streamlit завершился до запуска. Проверь установку зависимостей.")
        try:
            with urlopen(f"{base}/_stcore/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(0.5)
    raise TimeoutError("Не удалось дождаться запуска Streamlit.")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    args = [
        sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
        "--server.headless=true", f"--server.port={port}",
        "--server.address=127.0.0.1", "--browser.gatherUsageStats=false",
    ]
    process = subprocess.Popen(args, cwd=ROOT, env=environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_ready(base, process)
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:
                # Если браузер Playwright ещё не скачан, попробуем установленный Chrome.
                try:
                    browser = playwright.chromium.launch(channel="chrome", headless=True)
                except Exception:
                    raise RuntimeError(
                        "Не найден Chromium. Выполни: python -m playwright install chromium"
                    ) from exc
            try:
                for view, filename, heading in PAGES:
                    context = browser.new_context(
                        viewport={"width": 1660, "height": 1030},
                        device_scale_factor=1.3,
                        color_scheme="light",
                        locale="ru-RU",
                    )
                    page = context.new_page()
                    page.goto(f"{base}/?view={view}&capture=1", wait_until="domcontentloaded")
                    page.get_by_text(heading, exact=True).first.wait_for(timeout=45000)
                    page.locator(".hero").first.wait_for(timeout=20000)
                    # Дождёмся завершения начальной отрисовки графиков и таблиц.
                    page.wait_for_timeout(2200)
                    path = OUTPUT / f"{filename}.png"
                    page.screenshot(path=str(path), full_page=True, animations="disabled")
                    print(f"Сохранено: {path.relative_to(ROOT)}")
                    context.close()
            finally:
                browser.close()
        print("\nГотово! Изображения можно вставлять в Word или PDF.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
