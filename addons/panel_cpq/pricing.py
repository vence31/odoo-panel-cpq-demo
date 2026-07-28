"""Pure pricing logic for the Panel CPQ demo.

Deliberately has zero Odoo imports so it can be unit tested with plain
pytest, independent of a running Odoo instance.
"""

MATERIAL_RATES = {
    'clear': 2.75,
    'frosted': 3.10,
    'black': 3.40,
}

MATERIAL_LABELS = {
    'clear': 'Clear',
    'frosted': 'Frosted',
    'black': 'Black',
}

CUTTING_FEE = 15.00
MINIMUM_CHARGE = 35.00


def compute_price(length_in, width_in, thickness_mm, material):
    if material not in MATERIAL_RATES:
        raise ValueError(f"Unknown material: {material!r}")
    area_sqft = (length_in * width_in) / 144.0
    rate = MATERIAL_RATES[material]
    price = area_sqft * thickness_mm * rate + CUTTING_FEE
    return round(max(price, MINIMUM_CHARGE), 2)


def format_description(material, thickness_mm, length_in, width_in, instance_name):
    if material not in MATERIAL_LABELS:
        raise ValueError(f"Unknown material: {material!r}")
    label = MATERIAL_LABELS[material]
    return (
        f"Acrylic Panel — {label}, {thickness_mm}mm, "
        f"{length_in}in × {width_in}in [{instance_name}]"
    )
