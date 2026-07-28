import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "addons" / "panel_cpq"))

from pricing import compute_price, format_description  # noqa: E402


def test_compute_price_basic_clear_panel():
    price = compute_price(24, 18, 6, 'clear')
    assert price == 64.5


def test_compute_price_hits_minimum_charge_floor():
    price = compute_price(4, 4, 3, 'clear')
    assert price == 35.0


def test_compute_price_unknown_material_raises():
    try:
        compute_price(10, 10, 5, 'gold')
    except ValueError as exc:
        assert 'gold' in str(exc)
    else:
        assert False, "Expected ValueError for unknown material"


def test_format_description_uses_mm_and_instance_id():
    description = format_description('clear', 6, 24, 18, 'CPQ-00001')
    assert description == "Acrylic Panel — Clear, 6mm, 24in × 18in [CPQ-00001]"
