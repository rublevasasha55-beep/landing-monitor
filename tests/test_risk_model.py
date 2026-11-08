import pytest
from risk_model import at_risk_spend, risk_level, suggest_action


def test_hourly_spend():
    assert at_risk_spend(300, 40, 1) == 12000

def test_quarter_hour_half_share():
    assert at_risk_spend(300, 40, .5, 15) == 1500

def test_healthy_zero_risk():
    assert risk_level('ok', 50000) == 'Нет активного риска'

def test_critical_error():
    assert risk_level('error', 12000) == 'Критичный'
    assert 'согласовать' in suggest_action('error', 12000)

def test_invalid_share():
    with pytest.raises(ValueError):
        at_risk_spend(100, 20, 1.5)
