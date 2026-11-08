"""Безопасная базовая HTTP-проверка публичных лендингов.

Это НЕ полноценный браузерный тест, не эмуляция устройств и не 24/7-мониторинг.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

MAX_REDIRECTS = 3
MAX_HTML_BYTES = 1_500_000
TIMEOUT = (4, 10)


class CheckError(ValueError):
    """Понятная пользователю ошибка проверки адреса."""


@dataclass
class CheckResult:
    url: str
    final_url: str
    status: str  # ok, warning, error
    http_code: Optional[int]
    elapsed_ms: int
    has_html_form: Optional[bool]
    title: str
    detail: str


def check_public_url(url: str) -> str:
    """Проверяет синтаксис и разрешение хоста только в публичные IP.

    Важно: DNS-проверка не гарантирует защиту от DNS-rebinding.
    Демоприложение должно работать локально и не выставляться в общий доступ.
    """
    url = (url or "").strip()
    if not url or len(url) > 2048:
        raise CheckError("Укажи URL длиной до 2048 символов.")
    p = urlsplit(url)
    if p.scheme != "https":
        raise CheckError("Для ручной проверки требуется адрес, начинающийся с https://.")
    if not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise CheckError("Укажи публичный HTTPS-адрес без логина, пароля и нестандартного порта.")
    hostname = p.hostname.rstrip(".").lower()
    if hostname in ("localhost",) or hostname.endswith((".local", ".internal", ".localhost", ".test")):
        raise CheckError("Локальные и тестовые домены для сетевой проверки запрещены.")
    if "." not in hostname:
        raise CheckError("Нужен публичный домен, например https://example.com.")
    try:
        ips = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)]
    except (socket.gaierror, ValueError, OSError) as exc:
        raise CheckError("Не удалось разрешить доменное имя: {}".format(exc))
    if not ips or any(not ip.is_global for ip in ips):
        raise CheckError("Проверка частных или локальных IP-адресов запрещена.")
    return url


def run_http_check(url: str, require_form: bool = True) -> CheckResult:
    """GET-запрос к публичному HTTPS-ресурсу, без отправки формы и запуска JavaScript."""
    current = check_public_url(url)
    started = time.monotonic()
    try:
        with requests.Session() as sess:
            sess.trust_env = False  # Не используем прокси из окружения при сетевой проверке
            sess.headers.update({"User-Agent": "LandingMonitorMVP/0.1 (manual-readonly-check)"})
            for hop in range(MAX_REDIRECTS + 1):
                # Сами валидируем каждый переход, чтобы не следовать редиректам на локальные адреса.
                with sess.get(current, timeout=TIMEOUT, allow_redirects=False, stream=True) as resp:
                    code = int(resp.status_code)
                    if code in (301, 302, 303, 307, 308):
                        target = resp.headers.get("Location")
                        if not target or hop == MAX_REDIRECTS:
                            raise CheckError("Слишком много перенаправлений или отсутствует Location.")
                        current = check_public_url(urljoin(current, target))
                        continue
                    content_type = resp.headers.get("Content-Type", "").lower()
                    chunks = []
                    total = 0
                    for chunk in resp.iter_content(chunk_size=65536):
                        total += len(chunk)
                        if total > MAX_HTML_BYTES:
                            raise CheckError("Ответ больше 1,5 МБ; полная загрузка остановлена.")
                        chunks.append(chunk)
                    elapsed_ms = max(1, round((time.monotonic() - started) * 1000))
                    html = b"".join(chunks)
                    is_html = "html" in content_type or html[:100].lstrip().lower().startswith(b"<!doctype html")
                    soup = BeautifulSoup(html, "html.parser") if is_html else None
                    title = soup.title.get_text(" ", strip=True)[:130] if soup and soup.title else "Без заголовка"
                    form = bool(soup.find("form")) if soup is not None else None
                    if code >= 400:
                        status, detail = "error", "Сервер вернул HTTP {}.".format(code)
                    elif elapsed_ms > 3000:
                        status, detail = "warning", "HTML-ответ получен медленнее порога 3 с."
                    elif require_form and form is False:
                        status, detail = "warning", "Тег <form> не найден в HTML. JavaScript-формы эта проверка не видит."
                    elif require_form and form is None:
                        status, detail = "warning", "Ответ не похож на HTML; наличие формы не определено."
                    else:
                        status, detail = "ok", "HTTP-ответ получен. Работу формы и внешний вид необходимо проверять отдельно."
                    return CheckResult(url, current, status, code, elapsed_ms, form, title, detail)
    except CheckError:
        raise
    except requests.exceptions.RequestException as exc:
        return CheckResult(url, current, "error", None, max(1, round((time.monotonic() - started) * 1000)), None, "Недоступно", "Сетевая ошибка: {}".format(str(exc)[:240]))
    raise CheckError("Проверка не завершилась.")
