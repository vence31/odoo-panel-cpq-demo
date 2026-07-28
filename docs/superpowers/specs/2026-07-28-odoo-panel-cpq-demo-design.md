# Odoo Panel CPQ Demo — Design

## Purpose

A self-contained, runnable Odoo custom module that demonstrates real Odoo module
development skill (ORM, wizards, sequences, view inheritance, security) for use
as a portfolio artifact when bidding on Odoo/ERP freelance jobs. Modeled after
the requirements of a real job posting ("Odoo ERP + E-Commerce + Custom CPQ")
that asked for an acrylic-panel pricing configurator injecting a single line
item into Odoo quotations.

Scope for this pass: the CPQ module only (Sales app). The Odoo
Website/eCommerce demo page is an explicit fast-follow, not included here.

## Stack & Environment

- Docker Desktop on Windows (WSL2 backend), via `docker-compose.yml`:
  - `postgres:16`
  - `odoo:18.0`
- Custom addons path bind-mounted from the project folder so module code is
  editable on Windows and picked up by Odoo without rebuilding images.
- Project root: `C:\Users\vence\Documents\Odoo Panel CPQ Demo` (own git repo).

```
Odoo Panel CPQ Demo/
  docker-compose.yml
  addons/
    panel_cpq/          <- the Odoo module
  README.md             <- setup instructions + screenshots (portfolio writeup)
```

## Design Constraint (from the source job posting)

The real job explicitly asked to "avoid overengineering," "minimize custom
tables," and "follow native Odoo patterns." The module is deliberately
designed around this constraint — it's a detail worth echoing back to a
client in a real proposal, and it keeps the demo itself simple to build and
verify.

## Data Model

Only one new persistent table.

### `panel.cpq.wizard` (TransientModel)

Odoo's standard pattern for a configurator popup — transient, not a real
table.

- `material` — Selection: Clear / Frosted / Black acrylic. Rates are
  hardcoded constants in Python, not a separate materials table (a real
  client build might promote this to a settings model; that would be
  overengineering for a demo).
- `length_in` — Float
- `width_in` — Float
- `thickness_mm` — Float
- `sale_order_id` — Many2one `sale.order`, auto-filled from context
- `price` — Float, computed (onchange), readonly, live preview
- `description` — Char, computed (onchange), readonly, live preview
- Button: **Add to Quote**

### `panel.cpq.instance` (Model — the one new persistent table)

The audit/traceability record. Its auto-numbered `name` is the "instance ID"
called for in the source job's requirement ("Output: price, description,
instance ID").

- `name` — auto-numbered via an `ir.sequence` (e.g. `CPQ-00001`)
- `material`, `length_in`, `width_in`, `thickness_mm` — copied from the
  wizard at confirm time
- `price` — Float, stored
- `description` — Char, stored
- `sale_order_line_id` — Many2one `sale.order.line`, links back to the line
  it produced

## Pricing Formula

Simple, realistic, not tiered:

```
area_sqft = (length_in * width_in) / 144
price = area_sqft * thickness_mm * material_rate_per_sqft_per_mm + cutting_fee
price = max(price, minimum_charge)
```

`material_rate_per_sqft_per_mm`, `cutting_fee`, and `minimum_charge` are
module-level Python constants for this demo.

## Flow

1. User opens a quotation (`sale.order`) in the Odoo Sales app.
2. Clicks **"Add Panel (CPQ)"** button (added via view inheritance/xpath on
   the quotation form — no destructive edits to core `sale.order` or
   `sale.order.line` views).
3. Wizard opens: pick material, enter length/width/thickness. Price and
   description recompute live via `onchange`.
4. Clicks **Add to Quote**:
   - Creates one `panel.cpq.instance` record (sequence-numbered instance ID).
   - Injects one `sale.order.line` onto the quotation, with a generated
     description like `Acrylic Panel — Clear, 1/4in, 24in × 18in [CPQ-00001]`,
     quantity 1, `price_unit` = computed price.
   - Links the instance record to the created line.
5. Wizard closes; the new line is visible on the quotation immediately.

## Security

Single `ir.model.access.csv` entry granting the standard Sales User group
(`sales_team.group_sale_salesman`) full CRUD on both new models. No new
security groups for a demo of this scope.

## Testing / Verification Plan

- `docker compose up` boots cleanly; module installs with no errors in the
  Odoo log.
- Manual walkthrough: create a quotation → open the CPQ wizard → enter
  dimensions → confirm the live price/description update → Add to Quote →
  verify the resulting `sale.order.line` and the matching
  `panel.cpq.instance` record (including its sequence number).
- Repeat with at least two different material/dimension combinations,
  including dimensions small enough to hit the `minimum_charge` floor, to
  confirm the pricing formula behaves sensibly across cases.

## Deliverables

- Module source at `addons/panel_cpq/` in this repo — the concrete artifact
  to point to when a Freelancer proposal asks for "custom Odoo module
  examples."
- `README.md`: setup steps, a short explanation of the design decisions
  (especially the "minimize custom tables" alignment), and 3-4 screenshots
  of the working wizard and the resulting quotation line.
- Optional fast-follow: push to a public GitHub repo so the module can be
  linked directly in Freelancer proposals.
