"""Pytest test suite for System Monitor."""

from app.resources.system_monitor import get_system_resources


def test_system_monitor_resources():
    resources = get_system_resources()
    assert isinstance(resources, dict)
    assert "cpu_percent" in resources
    assert "ram_available_gb" in resources
    assert resources["ram_available_gb"] >= 0.0