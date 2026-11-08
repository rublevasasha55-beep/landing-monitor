"""Landing Monitor · light fintech concept for a business-analysis case.

All seeded landing data and browser/platform illustrations are synthetic.
Real checks are manual, HTTP-only, and limited to explicitly authorized public HTTPS URLs.
This is NOT an official T-Bank service or a 24/7 browser monitoring system.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from checker import CheckError, run_http_check
from storage import init_db, landings, recent_checks, incidents, save_check, set_incident_state
from risk_model import at_risk_spend, build_demo_risks, risk_level, suggest_action

st.set_page_config(
    page_title="Landing Monitor — Центр мониторинга",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()

INK = "#202328"
SUB = "#737D8D"
YELLOW = "#FFDD2D"
GREEN = "#22A77A"
AMBER = "#FFA72B"
RED = "#F36C65"
BLUE = "#487FF2"
BG = "#F7F8FA"

# Inline vector icons: crisp in the browser and exported screenshots; no external assets.
ICON_PATHS = {
    "home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
    "layers": '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7.07-7.07l-1.7 1.71"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7.07 7.07l1.7-1.71"/>',
    "pulse": '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
    "activity": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M5 12h4l2-4 3 8 2-4h3"/>',
    "alert": '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "bolt": '<path d="m13 2-9 12h7l-1 8 10-13h-7l0-7Z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7h.01"/>',
    "search": '<circle cx="10.5" cy="10.5" r="7.5"/><path d="m16 16 5 5"/>',
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    "monitor": '<rect x="2" y="4" width="20" height="15" rx="2"/><path d="M8 22h8M12 19v3"/>',
    "mobile": '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>',
    "code": '<path d="m8 5-6 7 6 7M16 5l6 7-6 7"/>',
    "arrow": '<path d="M4 12h15m-6-6 6 6-6 6"/>',
    "external": '<path d="M12 4h8v8M20 4l-9 9"/><path d="M20 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5"/>',
    "filter": '<path d="M4 7h16M7 12h10M10 17h4"/>',
    "shield": '<path d="M12 2 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6z"/><path d="m9 12 2 2 4-4"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 2 4 3 9 3s9-1 9-3V5M3 12c0 2 4 3 9 3s9-1 9-3"/>',
    "file": '<path d="M5 2h9l5 5v15H5z"/><path d="M14 2v5h5M8 12h8M8 16h8"/>',
}


def icon(name: str, size: int = 20, color: str = "currentColor") -> str:
    path = ICON_PATHS.get(name, ICON_PATHS["info"])
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true" focusable="false">{path}</svg>')


def h(value) -> str:
    return escape(str(value), quote=True)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --yellow:#ffdd2d;--ink:#202328;--muted:#737d8d;--base:#f7f8fa;--soft:#f0f2f5;}
html,body,.stApp,button,input,textarea,select,[data-testid="stMarkdownContainer"] {font-family:'Manrope',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif!important}
.stApp {background:var(--base);color:var(--ink)}
.block-container {max-width:1580px;padding:1.25rem 2.0rem 2.2rem 2.0rem;}
header[data-testid="stHeader"] {display:none!important} #MainMenu, footer{display:none!important}
[data-testid="stSidebar"] {background:#fff;border:0!important;box-shadow:7px 0 35px rgba(33,36,44,.035);width:252px!important;min-width:252px!important;max-width:252px!important}
[data-testid="stSidebar"] > div {width:252px!important}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding:1.5rem 1.05rem}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {display:none}
[data-testid="stSidebar"] hr {border-color:#edf0f3}
[data-testid="stAppViewContainer"] > .main {background:var(--base)}
[data-testid="stDecoration"] {display:none}
h1,h2,h3 {font-weight:800!important;color:var(--ink)!important;letter-spacing:-.035em}
h1 {font-size:32px!important;} h2{font-size:23px!important} h3{font-size:17px!important}
/* Top navigation and header */
.brand {display:flex;align-items:center;gap:12px;padding:5px 8px 5px 8px}
.brandmark {display:flex;align-items:center;justify-content:center;width:43px;height:43px;background:var(--yellow);border-radius:13px;color:#222;font-size:25px;font-weight:900;box-shadow:0 5px 12px rgba(255,221,45,.2)}
.brandcopy b {font-size:16px;letter-spacing:-.045em;color:#1b1d22}
.brandcopy small {display:block;font-size:10px;color:#8991a0;margin-top:4px;letter-spacing:-.01em}
.nav-heading {padding:27px 13px 8px;color:#9aa2af;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}
.nav-link {display:flex;align-items:center;gap:13px;padding:12px 14px;margin:3px 0;border-radius:13px;color:#31343b;text-decoration:none!important;font-size:13px;font-weight:650;transition:background .18s,color .18s}
.nav-link svg{flex:none} .nav-link:hover {background:#f6f7f9;color:#111!important}
.nav-link.active{background:#fff2b3;color:#24262b;font-weight:800}
.nav-link.active svg{color:#1f2125}
.sidemeta {margin-top:31px;padding:17px 15px;border-radius:15px;background:#f6f7f9;font-size:11px;line-height:1.65;color:#727b89}
.sidemeta b{font-size:11px;color:#34383f}.sidemeta .smallnote{margin-top:7px;color:#8d95a1}
.tophead {display:flex;align-items:center;justify-content:space-between;padding:4px 0 13px;gap:14px}
.tophead-left{color:#9299a4;font-size:10px;font-weight:850;letter-spacing:.13em;text-transform:uppercase}
.tophead-right{display:flex;align-items:center;gap:10px}
.top-icon{height:32px;width:32px;border-radius:50%;display:grid;place-items:center;background:white;box-shadow:0 3px 9px rgba(30,35,40,.04)}
.avatar{height:33px;width:33px;border-radius:50%;display:grid;place-items:center;background:#26272b;color:#fff;font-size:11px;font-weight:800}
.hero {position:relative;overflow:hidden;border-radius:22px;padding:20px 28px 23px;margin-bottom:16px;background:#fff;box-shadow:0 6px 25px rgba(25,30,40,.045)}
.hero::before{content:'';position:absolute;right:-35px;top:-88px;height:245px;width:330px;border-radius:49% 51% 52% 48%;transform:rotate(-23deg);background:linear-gradient(135deg,#fff9d5,#ffe277 52%,#fff 94%);opacity:.85}
.hero::after{content:'';position:absolute;right:80px;top:64px;height:160px;width:280px;border-radius:80% 10% 10% 70%;transform:rotate(-12deg);background:linear-gradient(45deg,rgba(255,217,50,.45),rgba(255,249,202,.05));opacity:.9}
.hero h1,.hero p,.hero .eyebrow{position:relative;z-index:1;max-width:80%}
.hero .eyebrow{font-size:10px;font-weight:850;color:#8992a0;letter-spacing:.13em;text-transform:uppercase}
.hero h1{font-size:31px!important;line-height:1.25;margin:8px 0 6px}
.hero p{font-size:12px;color:#727b87;line-height:1.55;margin:0}
/* Streamlit input row styled as light pill controls */
[data-testid="stSelectbox"] label,[data-testid="stTextInput"] label {font-size:11px!important;font-weight:750!important;color:#6e7785!important}
[data-testid="stSelectbox"] [data-baseweb="select"]>div,[data-testid="stTextInput"] input{border-radius:12px!important;border:1px solid #e7ebef!important;background:#fff!important;min-height:40px!important}
[data-testid="stSelectbox"] [data-baseweb="select"]>div:hover{border-color:#d3d8de!important}
.stButton button,[data-testid="stFormSubmitButton"] button{border-radius:12px!important;font-weight:800!important;min-height:41px!important;}
.stButton button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:#ffdd2d!important;color:#22252a!important;border:0!important}
.stButton button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{background:#ffd21a!important}
.stButton button[kind="secondary"]{background:white;border:1px solid #e6e9ef}
/* Global cards */
.kpi {background:#fff;box-shadow:0 8px 26px rgba(30,35,45,.055);border-radius:18px;padding:17px 17px 15px;min-height:119px}
.kpi-top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.kpi-label{font-size:10px;font-weight:750;color:#79828e;line-height:1.4}
.kpi-icon {display:grid;place-items:center;flex:none;width:35px;height:35px;border-radius:12px;background:#fff8da;color:#2b2d31}
.kpi-value{font-size:29px;line-height:1.25;font-weight:850;letter-spacing:-.055em;margin:7px 0 1px;color:#202328}
.kpi-desc{font-size:10px;color:#8d95a0;line-height:1.35}
.chart-title{font-size:15px;font-weight:850;letter-spacing:-.025em;color:#202328;margin-bottom:2px}
.chart-subtitle{font-size:10px;color:#929aa7;margin-bottom:2px}
/* Panels wrap native plotly and data widgets, avoiding fake drawings */
div[data-testid="column"]:has(.chart-title){background:#fff;border-radius:19px;padding:18px 20px 10px;box-shadow:0 8px 25px rgba(26,30,42,.045);min-width:0}
div[data-testid="column"]:has(.lower-panel-title){background:#fff;border-radius:19px;padding:16px 17px 12px;box-shadow:0 8px 25px rgba(26,30,42,.045);min-width:0}
.lower-panel-title{font-weight:850;font-size:14px;color:#252830;letter-spacing:-.018em;margin-bottom:10px}
.section-title{display:flex;align-items:center;justify-content:space-between;margin:18px 0 10px;font-size:14px;font-weight:850;letter-spacing:-.023em;color:#262a30}
.section-title a{font-size:11px;letter-spacing:normal;color:#6f7783;text-decoration:none;font-weight:700}
.section-title a:hover{color:#222}
.demo-note{display:flex;gap:8px;align-items:center;background:#fff7db;color:#6d6243;border-radius:12px;margin-bottom:15px;padding:9px 14px;font-size:11px}
.status-row{display:flex;gap:2px;overflow:hidden;border-radius:14px;height:20px;margin:18px 0 14px;background:#f4f5f6}
.status-row span{display:block;flex-shrink:0}
.legenditem{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid #f1f3f5;color:#59616d;font-size:11px}
.legenditem:last-child{border:0}.legenditem b{margin-left:auto;color:#30353b}
.legenddot{width:9px;height:9px;border-radius:50%;display:inline-block}
.incident-line{display:flex;align-items:center;gap:11px;background:#f9fafb;padding:11px 12px;border-radius:13px;margin:7px 0}
.incicon{width:35px;height:35px;border-radius:11px;display:grid;place-items:center;flex-shrink:0}
.incbody{flex:1;min-width:0}.incbody b{font-size:11px;color:#262930;display:block}.incbody small{color:#89919c;font-size:9px;display:block;margin-top:3px}
.tag{font-size:9px;padding:5px 8px;border-radius:999px;white-space:nowrap;font-weight:750}
.tag-error{background:#ffecea;color:#c14c42}.tag-warning{background:#fff3dc;color:#aa7517}.tag-ok{background:#e4f7ee;color:#168b5a}
.platformgrid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.platform{display:flex;gap:7px;align-items:center;background:#f6f7f9;border-radius:12px;padding:9px;color:#343940;font-size:10px;font-weight:700}
.platform .right{margin-left:auto;color:#738191;font-size:9px;font-weight:550}
.risk-feature{background:#fff;box-shadow:0 8px 26px rgba(30,35,45,.055);border-radius:18px;padding:16px 19px;border-left:4px solid #ffdd2d;margin:12px 0}
.risk-feature b{font-size:14px;color:#252830}.risk-feature p{font-size:11px;color:#727b89;line-height:1.5;margin:5px 0 3px}
.risk-number{font-weight:850;font-size:27px;letter-spacing:-.04em;color:#202328}
.risk-mono{font-variant-numeric:tabular-nums}
.mini-checks{width:100%;border-collapse:collapse;font-size:10px}
.mini-checks th{text-align:left;color:#8b93a0;font-weight:700;padding:8px 7px;border-bottom:1px solid #f0f2f4}
.mini-checks td{padding:10px 7px;border-bottom:1px solid #f3f4f6;color:#343942}
.mini-checks tr:last-child td{border-bottom:0}
.quick-hint{color:#8c95a1;font-size:10px;line-height:1.6;margin:6px 0 12px}
.minibadge{font-size:9px;background:#fff6dc;color:#8f6e13;border-radius:7px;padding:3px 7px}
[data-testid="stDataFrame"]{border-radius:14px;overflow:hidden}
[data-testid="stMetric"]{background:#fff;padding:12px 14px;border-radius:14px}
[data-testid="stAlert"]{border-radius:14px}
[data-testid="stExpander"]{border:1px solid #eceef2!important;border-radius:12px!important;background:#fff}
.stCaption,.stMarkdown p{line-height:1.6}
@media(max-width:1100px){.block-container{padding-left:1.3rem;padding-right:1.3rem}.kpi{padding:14px 12px;min-height:110px}.kpi-value{font-size:24px}.kpi-label{font-size:9px}}
@media(max-width:720px){.block-container{padding:1rem}.hero{padding:22px}.hero h1{font-size:24px!important}.hero:before,.hero:after{opacity:.28}}
</style>
""", unsafe_allow_html=True)

# Screenshot exporter disables Streamlit's own toolbar but keeps the actual app.
if st.query_params.get("capture", "0") == "1":
    st.markdown("<style>header[data-testid='stHeader'],[data-testid='stToolbar'],[data-testid='stDecoration']{display:none!important}</style>", unsafe_allow_html=True)


PAGE_MAP = [
    ("overview", "Обзор", "home"),
    ("landings", "Лендинги", "layers"),
    ("check", "Проверка URL", "link"),
    ("incidents", "Инциденты", "alert"),
    ("risks", "Бизнес-риски", "bolt"),
    ("about", "О решении", "info"),
]
current_page = st.query_params.get("view", "overview")
if current_page not in [x[0] for x in PAGE_MAP]:
    current_page = "overview"

with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brandmark">L</div><div class="brandcopy"><b>Landing Monitor</b><small>Контроль рекламных страниц</small></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-heading">Рабочее пространство</div>', unsafe_allow_html=True)
    nav_html = ''
    for page_id, title, symbol in PAGE_MAP:
        selected = ' active' if page_id == current_page else ''
        nav_html += f'<a class="nav-link{selected}" href="?view={page_id}">{icon(symbol,18)}<span>{h(title)}</span></a>'
    st.markdown(nav_html, unsafe_allow_html=True)
    st.markdown(
        '<div class="sidemeta">' + icon('shield',17,'#8d7b42') +
        ' <b>Демонстрационный режим</b><br>'
        'История проверок и часть инцидентов синтетические. HTTP-проверки запускаются вручную.'
        '<div class="smallnote">Независимый учебный прототип, не официальный интерфейс Т-Банка.</div></div>',
        unsafe_allow_html=True,
    )

sites = landings()
inc = incidents()


def shell(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        '<div class="tophead"><div class="tophead-left">Центр мониторинга лендингов / Концепт</div>'
        '<div class="tophead-right"><span class="top-icon">' + icon('bell',17) +
        '</span><span class="avatar">LM</span></div></div>', unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{h(eyebrow)}</div>'
        f'<h1>{h(title)}</h1><p>{h(subtitle)}</p></div>', unsafe_allow_html=True,
    )


def kpi(label: str, value: str, foot: str, symbol: str, hue: str = "#FFDD2D") -> None:
    st.markdown(
        '<div class="kpi"><div class="kpi-top"><span class="kpi-label">' + h(label) +
        '</span><span class="kpi-icon" style="background:' + hue + '1F">' + icon(symbol,19,INK) +
        '</span></div><div class="kpi-value">' + h(value) +
        '</div><div class="kpi-desc">' + h(foot) + '</div></div>',
        unsafe_allow_html=True,
    )


def section(title: str, action: str = "", target: str = "") -> None:
    link = f'<a href="?view={target}">{h(action)} →</a>' if target else ''
    st.markdown(f'<div class="section-title"><span>{h(title)}</span>{link}</div>', unsafe_allow_html=True)


def chart_title(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="chart-title">{h(title)}</div><div class="chart-subtitle">{h(subtitle)}</div>', unsafe_allow_html=True)


def little_title(title: str) -> None:
    st.markdown(f'<div class="lower-panel-title">{h(title)}</div>', unsafe_allow_html=True)


def tag(status: str) -> str:
    specs = {
        'ok': ('Работает', 'ok'), 'warning': ('Предупреждение', 'warning'),
        'error': ('Ошибка', 'error'),
    }
    label, cls = specs.get(str(status), ('Нет данных', 'warning'))
    return f'<span class="tag tag-{cls}">{label}</span>'


def line_chart(frame: pd.DataFrame, selected_period: int) -> None:
    if frame.empty:
        st.info("Проверок за выбранный период нет.")
        return
    df = frame.copy()
    df['day'] = pd.to_datetime(df['checked_at']).dt.date
    df['ok'] = df['status'].ne('error').astype(float)
    day = df.groupby('day')['ok'].mean().mul(100).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=day['day'], y=day['ok'], mode='lines+markers',
        line={'color':'#25282e', 'width':2.6},
        marker={'color':'#ffda26', 'size':8, 'line':{'color':'#343434','width':1}},
        fill='tozeroy', fillcolor='rgba(255,221,45,.12)',
        hovertemplate='%{x}<br>Доступность: %{y:.1f}%<extra></extra>',
    ))
    fig.update_layout(
        height=250, margin={'l':7,'r':9,'t':8,'b':9},
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font={'family':'Manrope, Arial','size':11,'color':'#73808b'},showlegend=False,
        xaxis={'showgrid':False,'showline':False,'tickfont':{'color':'#7e8793'},'tickformat':'%d %b'},
        yaxis={'range':[88,101], 'gridcolor':'#f0f1f4','zeroline':False,'ticksuffix':'%','dtick':2},
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False,'responsive':True})


def quick_check(compact: bool = False) -> None:
    if not compact:
        st.markdown('<div class="quick-hint">Введите адрес страницы, которую разрешено проверять. '
                    'Запрос выполняется вручную и не отправляет данные формы.</div>',unsafe_allow_html=True)
    with st.form('quick-check-' + ('small' if compact else 'full'),clear_on_submit=False):
        url = st.text_input('Адрес сайта', value='https://example.com', label_visibility='collapsed', placeholder='https://example.com')
        has_form = st.checkbox('Проверить наличие HTML-формы',value=False,key='form-option-'+str(compact))
        consent = st.checkbox('Разрешение на проверку подтверждаю',value=False,key='consent-'+str(compact))
        clicked = st.form_submit_button('Проверить URL',type='primary',use_container_width=True)
    if clicked:
        if not consent:
            st.warning('Подтверди право на проверку выбранного сайта.')
        else:
            try:
                with st.spinner('Получаем ответ сайта…'):
                    result = run_http_check(url,has_form)
                    save_check(url.strip(),'Ручная проверка',result,has_form)
                st.success('Проверка завершена и сохранена в истории.')
                a,b=st.columns(2)
                with a:st.metric('HTTP-код',result.http_code or 'Нет ответа')
                with b:st.metric('Получение HTML',f'{result.elapsed_ms} мс')
                st.markdown(f'**Заголовок:** {h(result.title)}')
                st.markdown(f'**Итог:** {h(result.detail)}')
                st.caption('HTML-ответ ≠ полная браузерная загрузка. Наличие формы не гарантирует, что она отправится.')
            except CheckError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error('Не удалось завершить проверку: '+str(exc)[:160])


if current_page == 'overview':
    shell('Обзор / Демонстрация','Рекламные страницы под контролем',
          'Доступность, скорость и проблемы пользовательского пути — в одном рабочем пространстве.')
    # Unlike the earlier prototype, these filters are functional for history and trend metrics.
    f1,f2,f3,f4 = st.columns([1.16,1,1,1],gap='small')
    with f1:
        environment = st.selectbox('Источник данных',['Демо + ручные проверки','Только демо','Ручные проверки'],index=0)
    with f2:
        device_filter = st.selectbox('Устройство',['Все устройства','Мобильный','Ноутбук'],index=0)
    with f3:
        browser_filter = st.selectbox('Браузер',['Все браузеры','Chrome','Safari','Firefox','HTTP-запрос'],index=0)
    with f4:
        period = st.selectbox('Период',['Последние 7 дней','Последние 24 часа','Последние 30 дней'],index=0)
    days = {'Последние 7 дней':7,'Последние 24 часа':1,'Последние 30 дней':30}[period]
    checks = recent_checks(days=days)
    if environment == 'Только демо':
        checks = checks[checks['source']=='demo']
    elif environment == 'Ручные проверки':
        checks = checks[checks['source']=='live']
    if device_filter != 'Все устройства':
        checks = checks[checks['device']==device_filter]
    if browser_filter != 'Все браузеры':
        checks = checks[checks['browser']==browser_filter]

    st.markdown('<div class="demo-note">'+icon('info',15,'#8f741c')+
        '<span>Показатели демонстрационные, если не выбран источник «Ручные проверки». Фоновой проверки 24/7 в этой версии нет.</span></div>',
        unsafe_allow_html=True)
    total = len(sites)
    bad = int(sites['status'].isin(['error','warning']).sum())
    uptime = f"{100*checks['status'].ne('error').mean():.1f}%" if len(checks) else '—'
    open_inc = int(inc['state'].ne('Решён').sum())
    avg_ms = f"{checks['response_ms'].dropna().mean()/1000:.1f} с" if checks['response_ms'].notna().any() else '—'
    values = [
        ('Лендингов',str(total),'в реестре','layers','#FFDD2D'),
        ('Доступность',uptime,'по выбранным проверкам','pulse','#24AD7C'),
        ('Требуют внимания',str(bad),'последний статус','alert','#FFC642'),
        ('Открытые инциденты',str(open_inc),'в локальной базе','bolt','#F27C6A'),
        ('Средний HTTP-ответ',avg_ms,'не полная загрузка','clock','#6D9EFA'),
    ]
    for col,(label,value,desc,symbol,hue) in zip(st.columns(5,gap='small'),values):
        with col:kpi(label,value,desc,symbol,hue)
    st.markdown('<div style="height:14px"></div>',unsafe_allow_html=True)
    left,right = st.columns([1.55,1],gap='medium')
    with left:
        chart_title('Динамика доступности','Доля HTTP-проверок без ошибки')
        line_chart(checks,days)
    with right:
        chart_title('Состояние лендингов','Последние известные результаты, независимо от фильтров')
        counts = sites['status'].value_counts()
        amounts = [int(counts.get('ok',0)),int(counts.get('warning',0)),int(counts.get('error',0))]
        v1,v2 = st.columns([1.08,1],gap='small')
        with v1:
            fig = go.Figure(go.Pie(
                values=amounts,labels=['Работают','Предупреждения','Ошибки'],hole=.73,
                marker={'colors':[GREEN,AMBER,RED],'line':{'color':'white','width':3}},
                direction='clockwise',sort=False,textinfo='none',hovertemplate='%{label}: %{value}<extra></extra>',
            ))
            fig.update_layout(
                showlegend=False,height=230,margin={'l':0,'r':0,'t':1,'b':0},
                paper_bgcolor='rgba(0,0,0,0)',
                annotations=[{'text':f'<b>{total}</b>', 'showarrow':False,
                              'font':{'size':24,'color':INK}}],
            )
            st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        with v2:
            st.markdown('<div style="height:35px"></div>',unsafe_allow_html=True)
            for label,amount,color in zip(['Работают','Предупреждения','Ошибки'],amounts,[GREEN,AMBER,RED]):
                st.markdown('<div class="legenditem"><i class="legenddot" style="background:'+color+'"></i>'+label+
                            '<b>'+str(amount)+'</b></div>',unsafe_allow_html=True)
            st.caption('Последний статус каждого URL')

    mid_left,mid_right=st.columns([1.55,1],gap='medium')
    with mid_left:
        little_title('Приоритетные инциденты')
        active=inc[inc['state']!='Решён'].head(3)
        if active.empty:st.success('Активных инцидентов не найдено')
        else:
            for _,r in active.iterrows():
                iscritical=r['severity']=='Критичный'
                sym='alert' if iscritical else 'clock'
                color=RED if iscritical else AMBER
                state='Критичный' if iscritical else str(r['severity'])
                st.markdown('<div class="incident-line"><div class="incicon" style="background:'+color+'20">'
                    +icon(sym,19,color)+'</div><div class="incbody"><b>'+h(r['name'])+' — '+h(r['issue'])+'</b><small>'
                    +h(r['details'])+'</small></div><span class="tag '+('tag-error' if iscritical else 'tag-warning')+'">'
                    +h(state)+'</span></div>',unsafe_allow_html=True)
        st.markdown('<a href="?view=incidents" style="font-size:11px;color:#6e7785;text-decoration:none;font-weight:750">Все инциденты →</a>',unsafe_allow_html=True)
    with mid_right:
        little_title('Платформы и браузеры')
        st.markdown('<div class="platformgrid">'+''.join(
            '<div class="platform">'+icon(sym,16,'#4d6078')+'<span>'+label+'</span><span class="right">план</span></div>'
            for sym,label in [('mobile','iPhone / Safari'),('mobile','Android / Chrome'),
                              ('monitor','Windows / Chrome'),('monitor','macOS / Safari'),
                              ('globe','Firefox'),('globe','WebKit')]
        )+'</div>',unsafe_allow_html=True)
        st.caption('Матрица — план будущих браузерных тестов. MVP пока не проверяет реальные устройства.')

    demo_risks = build_demo_risks(sites)
    if not demo_risks.empty:
        top_risk = demo_risks.iloc[0]
        st.markdown(
            '<div class="risk-feature"><b>' + icon('bolt',17,'#bd920f') +
            ' Бизнес-риски рекламных кампаний</b>'
            '<p>Отдельно от технических ошибок оцениваем расходы на клики, которые могут попасть на проблемную страницу. '
            'Это модель на синтетических CPC и трафике, не реальные потери.</p>'
            '<span class="risk-number">' + f"{demo_risks['risk_hour_rub'].sum():,.0f}".replace(',', ' ') + ' ₽/ч</span>'
            '<span style="font-size:11px;color:#808894"> · пример суммы по демонстрационным кампаниям</span>'
            '<div style="margin-top:8px"><a style="font-size:11px;font-weight:800;color:#6b5813" href="?view=risks">Открыть расчёт и рекомендации →</a></div></div>',
            unsafe_allow_html=True,
        )

    bottom_left,bottom_right = st.columns([1.55,1],gap='medium')
    with bottom_left:
        little_title('Последние проверки')
        last = checks.sort_values('checked_at',ascending=False).head(5) if len(checks) else checks
        if not len(last): st.caption('Нет проверок под выбранными фильтрами.')
        else:
            rows=''
            for _,r in last.iterrows():
                dt=pd.to_datetime(r['checked_at']).strftime('%d.%m %H:%M')
                rows+='<tr><td><b>'+h(r['name'])+'</b></td><td>'+h(r['device'])+' · '+h(r['browser'])+'</td><td>'+tag(r['status'])+'</td><td>'+h(r['response_ms'])+' мс</td><td>'+h(dt)+'</td></tr>'
            st.markdown('<table class="mini-checks"><thead><tr><th>Лендинг</th><th>Устройство / браузер</th><th>Статус</th><th>HTTP-ответ</th><th>Время</th></tr></thead><tbody>'+rows+'</tbody></table>',unsafe_allow_html=True)
        st.markdown('<a href="?view=landings" style="font-size:11px;color:#6e7785;text-decoration:none;font-weight:750">Открыть реестр →</a>',unsafe_allow_html=True)
    with bottom_right:
        little_title('Проверка URL')
        st.markdown('<div class="quick-hint">Реальная проверка доступности страницы по HTTPS — по вашему запросу.</div>',unsafe_allow_html=True)
        quick_check(compact=True)

elif current_page == 'landings':
    shell('Реестр','Лендинги и кампании','Найдите страницу, посмотрите её статус и историю проверок.')
    a,b,c = st.columns([2,1,1],gap='medium')
    with a: search=st.text_input('Поиск по названию или кампании',placeholder='Например, кредит или карта')
    with b: status=st.selectbox('Статус',['Все','Работает','Предупреждение','Ошибка'])
    with c: source=st.selectbox('Источник',['Все','Демо','Ручная проверка'])
    filtered=sites.copy()
    if search:
        filtered=filtered[filtered['name'].str.contains(search,case=False,regex=False,na=False)|filtered['campaign'].str.contains(search,case=False,regex=False,na=False)]
    if status!='Все':filtered=filtered[filtered['status']=={'Работает':'ok','Предупреждение':'warning','Ошибка':'error'}[status]]
    if source!='Все':filtered=filtered[filtered['source']==('demo' if source=='Демо' else 'live')]
    a,b,c = st.columns(3,gap='medium')
    with a:kpi('Найдено',str(len(filtered)),'после фильтрации','layers')
    with b:kpi('Работают',str(int((filtered['status']=='ok').sum())),'по последней проверке','check','#23aa78')
    with c:kpi('С проблемами',str(int(filtered['status'].isin(['warning','error']).sum())),'требуют внимания','alert','#F36C65')
    section('Список страниц')
    table=filtered[['name','campaign','priority','status','response_ms','owner','source']].rename(columns={
        'name':'Лендинг','campaign':'Кампания','priority':'Приоритет','status':'Статус','response_ms':'HTTP, мс',
        'owner':'Ответственный','source':'Источник'}).copy()
    table['Статус']=table['Статус'].map({'ok':'Работает','warning':'Предупреждение','error':'Ошибка'})
    table['Источник']=table['Источник'].map({'demo':'Демо','live':'Ручная'})
    st.dataframe(table,hide_index=True,use_container_width=True,height=330)
    if len(filtered):
        section('Карточка лендинга')
        options={f"{r['name']} — {r['campaign']}":int(r['id']) for _,r in filtered.iterrows()}
        sel=st.selectbox('Выбрать страницу',list(options.keys()))
        item=filtered.loc[filtered['id']==options[sel]].iloc[0]
        x,y,z=st.columns(3)
        with x:kpi('Статус',{'ok':'Работает','warning':'Предупреждение','error':'Ошибка'}.get(item['status'],'—'),'последняя проверка','pulse')
        with y:kpi('Время HTTP-ответа',f"{item['response_ms']} мс" if pd.notna(item['response_ms']) else '—','не полная загрузка','clock')
        with z:kpi('Приоритет',str(item['priority']),'настроен в реестре','alert')
        st.caption(f"URL: {item['url']} · {'Демонстрационная запись' if item['source']=='demo' else 'Ручная проверка'}")
        history=recent_checks(days=7)
        history=history[history['landing_id']==options[sel]]
        if not history.empty:
            fig=go.Figure(go.Scatter(x=pd.to_datetime(history['checked_at']),y=history['response_ms'],
                mode='lines',line={'color':INK,'width':2},fill='tozeroy',fillcolor='rgba(255,221,45,.18)'))
            fig.update_layout(height=240,margin={'l':10,'r':10,'t':12,'b':4},paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',yaxis_title='HTTP, мс',showlegend=False)
            fig.add_hline(y=3000,line_dash='dash',line_color=AMBER)
            st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})

elif current_page == 'check':
    shell('Ручная проверка','Проверка URL','Проверка доступности и HTML-формы по HTTPS — без отправки заявок.')
    st.info('Ручная проверка анализирует HTTP-ответ и HTML. Эмуляция iPhone, Safari и работа формы пока НЕ реализованы — это следующий этап проекта.')
    quick_check(compact=False)
    section('Что покажет полноценная система')
    x,y,z=st.columns(3,gap='medium')
    with x:
        st.markdown('<div class="kpi"><div class="kpi-top">'+icon('monitor',20)+
                    '<b>Проверка устройств</b></div><p class="quick-hint">Браузерный запуск на заданных разрешениях, в Chromium, Firefox и WebKit.</p></div>',unsafe_allow_html=True)
    with y:
        st.markdown('<div class="kpi"><div class="kpi-top">'+icon('check',20)+
                    '<b>Сценарий заявки</b></div><p class="quick-hint">Безопасная отправка тестовой формы в отдельном контуре.</p></div>',unsafe_allow_html=True)
    with z:
        st.markdown('<div class="kpi"><div class="kpi-top">'+icon('file',20)+
                    '<b>Доказательство</b></div><p class="quick-hint">Скриншот сбоя, шаг воспроизведения и время проверки.</p></div>',unsafe_allow_html=True)

elif current_page == 'incidents':
    shell('Управление сбоями','Инциденты','У кого проблема, насколько она важна и что сделано для устранения.')
    count=int(len(inc))
    active=int(inc['state'].ne('Решён').sum())
    critical=int(((inc['severity']=='Критичный') & inc['state'].ne('Решён')).sum())
    a,b,c=st.columns(3,gap='medium')
    with a:kpi('Всего инцидентов',str(count),'сохранены в SQLite','layers')
    with b:kpi('Активные',str(active),'ожидают действий','bolt','#FF9E82')
    with c:kpi('Критичные',str(critical),'включая демо','alert','#F36C65')
    section('История проблем')
    filter_status=st.selectbox('Состояние',['Все','Открыт','В работе','Решён'])
    subset=inc if filter_status=='Все' else inc[inc['state']==filter_status]
    if subset.empty:st.info('Ничего не найдено по выбранному статусу.')
    for _,entry in subset.iterrows():
        is_crit=str(entry['severity'])=='Критичный'
        sevtag='🔴' if is_crit else '🟠' if entry['severity']=='Средний' else '🔵'
        with st.expander(f"{sevtag} {entry['name']} — {entry['issue']}",expanded=is_crit and entry['state']!='Решён'):
            a,b=st.columns(2)
            with a:
                st.write('**Кампания:**',entry['campaign'])
                st.write('**Приоритет:**',entry['severity'])
                st.write('**Ответственный:**',entry['owner'])
            with b:
                st.write('**Состояние:**',entry['state'])
                st.write('**Источник:**','Демо' if entry['source']=='demo' else 'Ручная проверка')
                st.write('**Обнаружено:**',str(entry['created_at']).replace('T',' ')[:16])
            st.write(entry['details'])
            if entry['source']=='demo':st.caption('Демонстрационная ситуация, скриншот реального сбоя отсутствует.')
            states=['Открыт','В работе','Решён']
            idx=states.index(entry['state']) if entry['state'] in states else 0
            state=st.selectbox('Состояние инцидента',states,index=idx,key=f"state_{entry['id']}")
            if st.button('Сохранить',key=f"save_{entry['id']}",type='primary'):
                set_incident_state(int(entry['id']),state)
                st.rerun()
    st.caption('Смена статуса сохраняется. История изменений и уведомления предусмотрены в промышленной версии.')

elif current_page == 'risks':
    shell('Демонстрационная модель','Бизнес-риски рекламных кампаний',
          'Показываем не только факт сбоя, но и пример его возможного влияния на оплаченные рекламные переходы.')
    st.markdown('<div class="demo-note">'+icon('info',15,'#8f741c')+
        '<span><b>Все значения CPC, трафика и доли затронутых кликов — вымышленные.</b> '
        'Показатели ниже являются сценарием риска, а не подтверждёнными убытками или данными Т-Банка.</span></div>',
        unsafe_allow_html=True)
    frame = build_demo_risks(sites)
    risky = frame[frame['risk_hour_rub'] > 0]
    total_impact = float(risky['risk_hour_rub'].sum()) if not risky.empty else 0.0
    c1,c2,c3=st.columns(3,gap='small')
    with c1:kpi('Расходы под риском (модель)',f"{total_impact:,.0f}".replace(',',' ')+' ₽/ч',
                'по демонстрационным кампаниям','bolt','#FFDD2D')
    with c2:kpi('Затронутые кампании',str(len(risky)),'с предположительно затронутым трафиком','layers','#F36C65')
    with c3:kpi('Критичные риски',str((risky['priority']=='Критичный').sum()),
                'по демонстрационным правилам','alert','#F36C65')
    section('Кампании: приоритет по расходам под риском')
    if frame.empty:
        st.info('Демонстрационные кампании не найдены.')
    else:
        report=frame[['landing','campaign','status','clicks_hour','cpc_rub','affected_share','risk_hour_rub','priority']].copy()
        report['status']=report['status'].map({'ok':'Работает','warning':'Предупреждение','error':'Ошибка'})
        report['affected_share']=report['affected_share'].mul(100).round(0).astype(int).astype(str)+'%'
        report['risk_hour_rub']=report['risk_hour_rub'].map(lambda x:f"{x:,.0f}".replace(',',' ')+' ₽/ч')
        report.columns=['Лендинг','Кампания','Статус','Клики/ч','CPC, ₽','Затронуты','Расходы под риском','Приоритет']
        st.dataframe(report,use_container_width=True,hide_index=True,height=245)

    section('Калькулятор: что будет при конкретном сбое?')
    st.markdown('Параметры можно менять. Так рекламная команда оценивает масштаб ситуации до принятия решения.')
    if not frame.empty:
        names={f"{r['landing']} · {r['campaign']}":i for i,r in frame.iterrows()}
        selected=st.selectbox('Рекламная кампания',list(names),index=0)
        row=frame.loc[names[selected]]
        col1,col2=st.columns([1.18,1],gap='medium')
        with col1:
            v1,v2=st.columns(2,gap='small')
            with v1:
                clicks=st.number_input('Переходов в час',min_value=0,max_value=1000000,value=int(row['clicks_hour']),step=10)
                share=st.slider('Доля затронутых переходов, %',0,100,int(round(100*row['affected_share'])),step=5)
            with v2:
                cpc=st.number_input('Средняя цена клика, ₽',min_value=0.0,max_value=100000.0,value=float(row['cpc_rub']),step=1.0)
                duration=st.number_input('Длительность сбоя, минут',min_value=0,max_value=1440,value=60,step=15)
        hour=at_risk_spend(clicks,cpc,share/100.0,60)
        period_amount=at_risk_spend(clicks,cpc,share/100.0,duration)
        with col2:
            st.markdown('<div class="risk-feature"><b>Оценка расходов под риском</b><br>'
                '<span class="risk-number">'+f"{period_amount:,.0f}".replace(',',' ')+' ₽</span>'
                '<p>За заданное время сбоя · '+f"{hour:,.0f}".replace(',',' ')+' ₽/ч при неизменном трафике</p></div>',
                unsafe_allow_html=True)
            st.write('**Приоритет:**',risk_level(str(row['status']),hour))
            st.write('**Ответственный:**',row['owner'])
            st.info(suggest_action(str(row['status']),hour))
        st.caption('Формула: переходы/ч × CPC × доля затронутых переходов × длительность (ч). '
                   'Она оценивает бюджет, потенциально связанный с проблемным трафиком, '
                   'а не чистый убыток, недополученную прибыль или потерянные заявки.')
        st.caption('Сценарный расчёт не останавливает рекламу автоматически. Приоритеты, допустимый риск и действия согласуются с рекламной командой.')

    section('Чем это отличается от обычного технического мониторинга')
    st.markdown('Вместо сообщения «HTTP 503» специалист видит **какая кампания затронута, сколько '
                'оплаченных переходов потенциально рискует не завершиться заявкой, кому сообщить о проблеме** '
                'и стоит ли рассмотреть временное ограничение трафика.')
    st.markdown('**Для промышленной версии:** интеграция с рекламной статистикой (расход, клики, CPC, активность), '
                'верификация пользовательского сценария до заявки, скриншот сбоя и правила согласования остановки кампаний.')

else:
    shell('Архитектура / Концепт' ,'Как это может работать 24/7',
          'Проверка доступности, скорости и ключевых пользовательских действий с автоматической реакцией на сбои.')
    section('Предлагаемый процесс мониторинга')
    stages=[('Реестр URL','Кампания, владелец, приоритет'),('Планировщик','Запуск проверок по расписанию'),
            ('Мониторинг','HTTP, браузеры, формы и скорость'),('Инциденты','Приоритет, ответственный, уведомление')]
    cols=st.columns(4,gap='medium')
    for col,(name,detail) in zip(cols,stages):
        with col:st.markdown('<div class="kpi"><b>'+h(name)+'</b><p class="quick-hint">'+h(detail)+'</p></div>',unsafe_allow_html=True)
    section('Что реализовано')
    st.write('Визуальный дашборд, синтетическая история проверок, реестр лендингов, ручная HTTP-проверка разрешённых HTTPS-сайтов и сохранение статуса инцидента в SQLite.')
    section('Что требуется для запуска 24/7')
    st.write('Серверный планировщик, независимые браузерные агенты по устройствам и геолокациям, безопасная тестовая отправка формы, уведомления, интеграция с рекламными кампаниями, журнал действий и разграничение прав.')
    st.info('Предложенная архитектура — проектное решение. Эти функции не выданы за уже реализованные в MVP.')

st.markdown('<div style="height:18px"></div>',unsafe_allow_html=True)
st.caption('Landing Monitor · независимый демонстрационный прототип для кейса бизнес-аналитика · не официальный сервис Т-Банка')
