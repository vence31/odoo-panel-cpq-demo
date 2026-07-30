# Odoo Panel CPQ Demo

A custom Odoo 18 module demonstrating a CPQ (Configure-Price-Quote) style
configurator: a Sales user picks a material and dimensions for an acrylic
panel, sees a live-computed price, and injects a single priced line into
an Odoo quotation.

Built as a focused portfolio piece modeled on a real freelance job
requirement (Odoo ERP + custom acrylic-panel CPQ), deliberately scoped to
match that job's own stated constraints: avoid overengineering, minimize
custom tables, follow native Odoo patterns.

## What it demonstrates

- Odoo ORM: models, computed fields, sequences, `TransientModel` wizards
- View inheritance (adding a button to the native Sales quotation form
  without modifying the core view destructively)
- A minimal, native-pattern approach: one new persistent table
  (`panel.cpq.instance`, the audit/instance-ID record), a transient
  wizard, and a small `sale.order` extension — no bespoke schema sprawl
- A pure-Python pricing core (`pricing.py`) kept free of Odoo imports and
  covered by plain pytest unit tests

## Pricing formula

```
area_sqft = (length_in * width_in) / 144
price = area_sqft * thickness_mm * material_rate + cutting_fee
price = max(price, minimum_charge)
```

Material rates, cutting fee, and minimum charge are demo constants in
`addons/panel_cpq/pricing.py`.

## Running it locally

Requires Docker Desktop.

```bash
docker compose up -d
```

Open `http://localhost:8069`, create a database (demo data off), then
install the "Panel CPQ Demo" app from the Apps menu.

On any quotation, click **Add Panel (CPQ)** in the header, fill in
material and dimensions, and click **Add to Quote**.

## Running the pricing unit tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Status

Fully implemented and verified: the module installs cleanly, the pricing
formula is unit tested (see above), and the full wizard → quotation-line
flow has been verified end-to-end (normal-size and minimum-charge-floor
scenarios) against a real running Odoo instance. Screenshots can be
captured by running the module locally using the Docker Compose stack
and following the setup instructions above.
