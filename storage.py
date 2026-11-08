"""SQLite-хранилище и правдоподобные, но полностью синтетические демо-данные."""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "storage" / "monitor.sqlite3"

LANDINGS = [
    ("Кредитная карта", "card", "Карты · Поиск", "Высокий", "https://example.com/card", "Команда карт", 1),
    ("Дебетовая карта", "debit", "Карты · РСЯ", "Высокий", "https://example.com/debit", "Команда карт", 1),
    ("Автокредит", "auto", "Кредиты · Поиск", "Высокий", "https://example.com/auto", "Команда кредитов", 1),
    ("Вклад", "deposit", "Вклады · Поиск", "Высокий", "https://example.com/deposit", "Команда вкладов", 1),
    ("Накопительный счёт", "savings", "Вклады · РСЯ", "Средний", "https://example.com/savings", "Команда вкладов", 1),
    ("Ипотека", "mortgage", "Кредиты · РСЯ", "Средний", "https://example.com/mortgage", "Команда кредитов", 1),
    ("Страхование путешествий", "travel", "Страхование · Поиск", "Средний", "https://example.com/travel", "Страхование", 1),
    ("Кредит наличными", "cash", "Кредиты · Поиск", "Высокий", "https://example.com/cash", "Команда кредитов", 1),
    ("Инвестиции", "invest", "Инвестиции · Поиск", "Средний", "https://example.com/invest", "Инвестиции", 1),
    ("Сервис для бизнеса", "business", "Бизнес · Поиск", "Высокий", "https://example.com/business", "Бизнес-продукты", 1),
    ("Премиум", "premium", "Карты · РСЯ", "Средний", "https://example.com/premium", "Команда карт", 1),
    ("Подписка", "subscription", "Карты · Поиск", "Низкий", "https://example.com/subscription", "Команда карт", 1),
]


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    with connect() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS landings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
              campaign TEXT NOT NULL, priority TEXT NOT NULL,
              url TEXT UNIQUE NOT NULL, owner TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1, source TEXT NOT NULL DEFAULT 'demo'
            );
            CREATE TABLE IF NOT EXISTS checks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              landing_id INTEGER NOT NULL REFERENCES landings(id),
              checked_at TEXT NOT NULL, status TEXT NOT NULL,
              response_ms INTEGER, http_code INTEGER,
              form_found INTEGER, device TEXT NOT NULL,
              browser TEXT NOT NULL, details TEXT,
              source TEXT NOT NULL DEFAULT 'demo'
            );
            CREATE INDEX IF NOT EXISTS checks_idx ON checks(landing_id,checked_at);
            CREATE TABLE IF NOT EXISTS incidents (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              landing_id INTEGER NOT NULL REFERENCES landings(id),
              created_at TEXT NOT NULL, severity TEXT NOT NULL,
              issue TEXT NOT NULL, details TEXT NOT NULL,
              state TEXT NOT NULL DEFAULT 'Открыт',
              owner TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'demo'
            );
        """)
        count = con.execute("SELECT COUNT(*) FROM landings").fetchone()[0]
        if count:
            return
        con.executemany("INSERT INTO landings (name,slug,campaign,priority,url,owner,active) VALUES (?,?,?,?,?,?,?)", LANDINGS)
        rng = random.Random(84)
        now = datetime.now().replace(second=0,microsecond=0)
        records = []
        for site_id in range(1, len(LANDINGS)+1):
            for slot in range(7*12):
                when = now - timedelta(hours=2*(7*12-1-slot))
                # Синтетические события только для демонстрации интерфейса.
                r = rng.random()
                bad = r < (0.07 if site_id in (3,4,7) else 0.014)
                slow = (not bad) and r < (0.19 if site_id in (4,7) else 0.055)
                status = "error" if bad else "warning" if slow else "ok"
                ms = rng.randint(3600, 6400) if slow else rng.randint(850, 2400)
                code = 503 if bad else 200
                details = "Ошибка HTTP 503" if bad else "Превышено 3 с" if slow else "Проверка прошла"
                browser = rng.choice(("Chrome", "Safari", "Firefox"))
                device = "Мобильный" if browser == "Safari" else rng.choice(("Ноутбук", "Мобильный"))
                records.append((site_id,when.isoformat(timespec="seconds"),status,ms,code,1,device,browser,details))
        # Для демонстрации фиксируем актуальные проблемы у трёх страниц.
        override = {3:("error",503,1700,"Форма недоступна"), 4:("warning",200,5300,"Медленный ответ"), 7:("error",503,900,"Сайт не отвечает")}
        for site_id,(status,code,ms,details) in override.items():
            indexes = [i for i,x in enumerate(records) if x[0] == site_id]
            idx = indexes[-1]
            row = list(records[idx])
            row[2],row[3],row[4],row[8] = status,ms,code,details
            records[idx] = tuple(row)
        con.executemany("""
          INSERT INTO checks (landing_id,checked_at,status,response_ms,http_code,form_found,device,browser,details)
          VALUES (?,?,?,?,?,?,?,?,?)
        """, records)
        incidents = [
            (3,now-timedelta(minutes=18),"Критичный","Форма заявки недоступна","Сбой воспроизводится в Chrome на мобильном профиле.","Открыт","Команда кредитов"),
            (7,now-timedelta(minutes=39),"Критичный","HTTP 503","Страница страхования периодически не открывается.","В работе","Страхование"),
            (4,now-timedelta(hours=2),"Средний","Медленная загрузка","Время ответа HTML превышает 3 секунды.","Открыт","Команда вкладов"),
            (9,now-timedelta(days=1),"Низкий","Временное замедление","Порог превышен в одной серии проверок.","Решён","Инвестиции"),
        ]
        con.executemany("""
          INSERT INTO incidents (landing_id,created_at,severity,issue,details,state,owner)
          VALUES (?,?,?,?,?,?,?)
        """, [(i,dt.isoformat(timespec="seconds"),sev,issue,details,state,owner) for i,dt,sev,issue,details,state,owner in incidents])


def landings():
    with connect() as con:
        return pd.read_sql_query("""
          SELECT l.*, c.checked_at, c.status, c.response_ms, c.http_code, c.source AS check_source
          FROM landings l LEFT JOIN checks c ON c.id = (
            SELECT c2.id FROM checks c2 WHERE c2.landing_id=l.id
            ORDER BY c2.checked_at DESC, c2.id DESC LIMIT 1
          ) ORDER BY l.id
        """, con)


def recent_checks(days=7):
    since = (datetime.now()-timedelta(days=days)).isoformat(timespec="seconds")
    with connect() as con:
        return pd.read_sql_query("""
           SELECT c.*, l.name, l.campaign FROM checks c
           JOIN landings l ON l.id = c.landing_id WHERE c.checked_at>=?
           ORDER BY c.checked_at ASC
        """, con, params=(since,))


def incidents():
    with connect() as con:
        return pd.read_sql_query("""
           SELECT i.*,l.name,l.campaign,l.url FROM incidents i
           JOIN landings l ON i.landing_id=l.id
           ORDER BY CASE WHEN i.state='Решён' THEN 1 ELSE 0 END,
                CASE i.severity WHEN 'Критичный' THEN 0 WHEN 'Высокий' THEN 1 ELSE 2 END,
                i.created_at DESC
        """, con)


def set_incident_state(incident_id, state):
    if state not in ("Открыт", "В работе", "Решён"):
        raise ValueError("Неподдерживаемое состояние")
    with connect() as con:
        con.execute("UPDATE incidents SET state=? WHERE id=?", (state, int(incident_id)))


def save_check(url, name, result, require_form):
    """Сохранить ручную сетевую проверку. Без автоматического запуска по расписанию."""
    with connect() as con:
        cur = con.execute("SELECT id FROM landings WHERE url=?", (url,))
        row = cur.fetchone()
        if row:
            landing_id = int(row[0])
        else:
            slug = "manual-{}".format(int(datetime.now().timestamp()*1000000))
            cur = con.execute("""
              INSERT INTO landings(name,slug,campaign,priority,url,owner,active,source)
              VALUES(?,?,'Ручная проверка','Низкий',?,'Не назначен',1,'live')
            """, ((name or result.title or "Проверка URL")[:90],slug,url))
            landing_id = cur.lastrowid
        con.execute("""
          INSERT INTO checks(landing_id,checked_at,status,response_ms,http_code,form_found,device,browser,details,source)
          VALUES(?,?,?,?,?,?,?,?,?,'live')
        """, (landing_id,datetime.now().isoformat(timespec="seconds"),result.status,result.elapsed_ms,result.http_code,
              (None if result.has_html_form is None else int(result.has_html_form)),"HTTP (без эмуляции)","requests",result.detail))
        if result.status in ("error", "warning"):
            existed = con.execute("SELECT 1 FROM incidents WHERE landing_id=? AND state!='Решён' AND source='live' LIMIT 1",(landing_id,)).fetchone()
            if not existed:
                severity = "Критичный" if result.status == "error" else "Средний"
                con.execute("""
                  INSERT INTO incidents(landing_id,created_at,severity,issue,details,state,owner,source)
                  VALUES(?,?,?,?,?,'Открыт','Не назначен','live')
                """, (landing_id, datetime.now().isoformat(timespec="seconds"),severity,
                      "Ошибка HTTP" if result.status == "error" else "Предупреждение при проверке",result.detail))
    return landing_id
