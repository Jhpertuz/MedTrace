import pytest
from app.services import calcular_prioridad


def test_monitor_example_is_high():
    assert calcular_prioridad("degradado", "diagnostico_terapia", 1, "alto", 2) == (56, "alta")


def test_bed_example_is_low():
    assert calcular_prioridad("sin_impacto", "apoyo", 2, "bajo", 0) == (15, "baja")


def test_override_is_critical_below_seventy():
    assert calcular_prioridad("detiene_servicio", "apoyo", 0, "bajo", 0) == (60, "critica")


def test_ventilator_without_backup_uses_supplied_usage():
    assert calcular_prioridad("detiene_servicio", "soporte_vital", 0, "bajo", 0) == (77, "critica")


@pytest.mark.parametrize("score_inputs, priority", [
    (("sin_impacto", "apoyo", 1, "medio", 1), "baja"),
    (("sin_impacto", "apoyo", 0, "bajo", 0), "media"),
    (("degradado", "diagnostico_terapia", 1, "bajo", 1), "media"),
    (("degradado", "apoyo", 0, "bajo", 1), "alta"),
    (("detiene_servicio", "apoyo", 2, "alto", 3), "alta"),
    (("detiene_servicio", "soporte_vital", 2, "alto", 0), "critica"),
])
def test_priority_ranges(score_inputs, priority):
    assert calcular_prioridad(*score_inputs)[1] == priority


@pytest.mark.parametrize("count, contribution", [(0, 0), (1, 5), (2, 5), (3, 15)])
def test_recurrence_levels(count, contribution):
    base = calcular_prioridad("sin_impacto", "apoyo", 2, "bajo", count)[0]
    assert base == 15 + contribution


@pytest.mark.parametrize("args", [("bad", "apoyo", 0, "bajo", 0), ("sin_impacto", "bad", 0, "bajo", 0), ("sin_impacto", "apoyo", -1, "bajo", 0)])
def test_invalid_factors(args):
    with pytest.raises(ValueError): calcular_prioridad(*args)
