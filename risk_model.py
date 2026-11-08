"""Отдельная модель бизнес-риска для учебного MVP.

Все объёмы трафика и CPC синтетические. Оценка не является финансовым
убытком банка и не предполагает доступа к рекламным системам.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignScenario:
    landing_slug: str
    campaign_name: str
    clicks_hour: int
    cpc_rub: float
    default_affected_share: float  # 0..1, только предположение


DEMO_CAMPAIGNS = (
    CampaignScenario('auto', 'Автокредит · Поиск', 300, 40.0, 1.00),
    CampaignScenario('travel', 'Страхование путешествий · Поиск', 180, 55.0, 1.00),
    CampaignScenario('deposit', 'Вклад · Поиск', 240, 32.0, 0.30),
    CampaignScenario('card', 'Кредитная карта · Поиск', 420, 45.0, 0.25),
    CampaignScenario('cash', 'Кредит наличными · Поиск', 150, 38.0, 0.25),
)


def at_risk_spend(clicks_hour: float, cpc_rub: float, affected_share: float, duration_minutes: float = 60.0) -> float:
    """Оценка рекламных расходов, связанных с потенциально затронутыми кликами.

    НЕ оценка реальных потерь или числа потерянных заявок.
    """
    if clicks_hour < 0 or cpc_rub < 0 or duration_minutes < 0 or not 0 <= affected_share <= 1:
        raise ValueError('Недопустимое значение входного параметра')
    return clicks_hour * (duration_minutes / 60.0) * cpc_rub * affected_share


def risk_level(status: str, amount_per_hour: float) -> str:
    """Иллюстративная матрица приоритетов, пороги требуют бизнес-согласования."""
    if status == 'ok' or amount_per_hour <= 0:
        return 'Нет активного риска'
    if status == 'error' and amount_per_hour >= 8000:
        return 'Критичный'
    if amount_per_hour >= 2500:
        return 'Высокий'
    return 'Средний'


def suggest_action(status: str, hourly_amount: float) -> str:
    """Рекомендация специалисту; не автоматическое отключение рекламы."""
    level=risk_level(status,hourly_amount)
    if level == 'Критичный':
        return ('Срочно уведомить владельца кампании и дежурную команду. '
                'Подтвердить сбой и согласовать временное ограничение трафика на лендинг.')
    if level == 'Высокий':
        return ('Проверить сбой повторно, назначить ответственного и оценить '
                'временное перераспределение рекламных переходов.')
    if level == 'Средний':
        return ('Назначить проверку проблемной платформы, зафиксировать '
                'масштаб затронутого трафика и контролировать восстановление.')
    return 'Продолжить мониторинг по расписанию; срочных действий не требуется.'


def build_demo_risks(sites):
    """Возвращает оценки для демонстрационных кампаний и последних статусов URL."""
    import pandas as pd
    rows=[]
    for cfg in DEMO_CAMPAIGNS:
        s=sites[sites['slug']==cfg.landing_slug]
        if s.empty or str(s.iloc[0].get('source','demo')) != 'demo':
            continue
        landing=s.iloc[0]
        status=str(landing['status'])
        share=0.0 if status=='ok' else cfg.default_affected_share
        amount=at_risk_spend(cfg.clicks_hour,cfg.cpc_rub,share)
        rows.append({
            'landing':str(landing['name']), 'slug':cfg.landing_slug,
            'campaign':cfg.campaign_name, 'status':status,
            'owner':str(landing['owner']), 'clicks_hour':cfg.clicks_hour,
            'cpc_rub':cfg.cpc_rub, 'affected_share':share,
            'risk_hour_rub':round(amount,2),
            'priority':risk_level(status,amount),
        })
    return pd.DataFrame(rows).sort_values('risk_hour_rub',ascending=False).reset_index(drop=True)
