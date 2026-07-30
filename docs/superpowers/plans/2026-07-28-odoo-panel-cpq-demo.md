# Odoo Panel CPQ Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable Odoo 18 custom module (`panel_cpq`) that lets a Sales user configure an acrylic panel (material, dimensions) from a quotation, see a live computed price, and inject a single priced line into that quotation — as a portfolio artifact proving real Odoo module development skill.

**Architecture:** Docker Compose runs Postgres 16 + Odoo 18.0 with a bind-mounted custom addons folder. The module has one pure-Python pricing module (no Odoo imports, unit-tested with plain pytest), one persistent model (`panel.cpq.instance`, the audit/instance-ID record), one transient wizard model (`panel.cpq.wizard`, the configurator popup), and a single added button on the native `sale.order` form. No core views or models are modified destructively — only extended via inheritance.

**Tech Stack:** Docker Desktop (WSL2 backend), Docker Compose, `postgres:16`, `odoo:18.0`, Python 3 (host, for pytest), pytest.

## Global Constraints

- Odoo version: 18.0 Community, official `odoo:18.0` Docker image.
- Postgres: official `postgres:16` Docker image.
- Custom addons bind mount: `./addons` (host) → `/mnt/extra-addons` (container).
- Module technical name: `panel_cpq`.
- Pricing constants (module-level Python constants, not configurable via UI for this demo):
  - `MATERIAL_RATES = {'clear': 2.75, 'frosted': 3.10, 'black': 3.40}` ($ per sqft per mm thickness)
  - `CUTTING_FEE = 15.00`
  - `MINIMUM_CHARGE = 35.00`
- Formula: `price = round(max(area_sqft * thickness_mm * material_rate + CUTTING_FEE, MINIMUM_CHARGE), 2)` where `area_sqft = (length_in * width_in) / 144.0`.
- `addons/panel_cpq/pricing.py` must have **zero Odoo imports** so it is unit-testable standalone with plain pytest, independent of a running Odoo instance.
- Minimize custom tables: exactly **one** new persistent model (`panel.cpq.instance`). The wizard is a `TransientModel` (not a real table). No new security groups — reuse `sales_team.group_sale_salesman`. No schema changes to core `sale.order` or `sale.order.line`.
- Sequence for instance IDs: code `panel.cpq.instance`, prefix `CPQ-`, padding `5` (produces `CPQ-00001`, `CPQ-00002`, ...).
- Line injection uses a generic placeholder `product.product` record (a data record, not a schema change) so the injected `sale.order.line` behaves like a normal Odoo sales line for invoicing/reporting.
- Description format (uses mm consistently, since the field is `thickness_mm`): `Acrylic Panel — {Material}, {thickness}mm, {length}in × {width}in [{instance_name}]`.
- Project root: `C:\Users\vence\Documents\Odoo Panel CPQ Demo`, git repo, remote `https://github.com/vence31/odoo-panel-cpq-demo` (public, already pushed with the design spec).

---

## File Structure

```
Odoo Panel CPQ Demo/
  .gitignore
  docker-compose.yml
  requirements-dev.txt
  README.md
  docs/
    screenshots/
      (populated during manual verification)
  tests/
    test_pricing.py
  addons/
    panel_cpq/
      __init__.py
      __manifest__.py
      pricing.py
      models/
        __init__.py
        sale_order.py
        panel_cpq_instance.py
        panel_cpq_wizard.py
      views/
        sale_order_views.xml
        panel_cpq_instance_views.xml
        panel_cpq_wizard_views.xml
      security/
        ir.model.access.csv
      data/
        panel_cpq_sequence.xml
        panel_cpq_product_data.xml
```

---

### Task 1: Environment Setup — Docker Desktop + Postgres/Odoo stack

**Files:**
- Create: `docker-compose.yml`
- Create: `.gitignore`

**Interfaces:**
- Produces: a running Odoo instance reachable at `http://localhost:8069`, with a database named `panel_cpq_demo`, that later tasks install the `panel_cpq` module into.

- [ ] **Step 1: Install Docker Desktop**

Run:
```bash
winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
```
Expected: winget reports successful install. Docker Desktop requires the WSL2 backend — if prompted during first launch to enable WSL2 or restart Windows, do so now. **This step needs a human at the keyboard for the first-launch EULA/WSL2 prompts and a possible restart — it cannot be fully unattended.** After any restart, launch Docker Desktop and wait until its whale icon shows "Docker Desktop is running."

- [ ] **Step 2: Verify Docker works**

Run: `docker --version && docker ps`
Expected: version string (e.g. `Docker version 27.x.x`) and an empty container list with no connection errors.

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 4: Write `docker-compose.yml`**

```yaml
services:
  web:
    image: odoo:18.0
    depends_on:
      - db
    ports:
      - "8069:8069"
    volumes:
      - odoo-web-data:/var/lib/odoo
      - ./addons:/mnt/extra-addons
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=odoo
      - POSTGRES_USER=odoo
    volumes:
      - odoo-db-data:/var/lib/postgresql/data

volumes:
  odoo-web-data:
  odoo-db-data:
```

- [ ] **Step 5: Start the stack**

Run: `docker compose up -d`
Expected: `docker compose ps` shows both `web` and `db` services in `running`/`healthy` state.

- [ ] **Step 6: Create the database via the web UI**

Using a browser, navigate to `http://localhost:8069`. Odoo shows the "Create Database" screen (no databases exist yet). Fill in:
- Database name: `panel_cpq_demo`
- Email: any placeholder, e.g. `admin@example.com`
- Password: any placeholder, e.g. `admin`
- Uncheck "Demo data" (keep the instance minimal)

Click "Create database". Expected: after a short load, the Odoo backend loads showing the Apps/dashboard screen — confirms Postgres + Odoo are wired together correctly.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .gitignore
git commit -m "Add Docker Compose stack for Postgres + Odoo 18"
git push
```

---

### Task 2: Pricing logic module with unit tests

**Files:**
- Create: `addons/panel_cpq/pricing.py`
- Create: `tests/test_pricing.py`
- Create: `requirements-dev.txt`

**Interfaces:**
- Produces: `compute_price(length_in: float, width_in: float, thickness_mm: float, material: str) -> float` and `format_description(material: str, thickness_mm: float, length_in: float, width_in: float, instance_name: str) -> str`, both pure functions with no Odoo dependency. These are imported by `models/panel_cpq_wizard.py` in Task 5.

- [ ] **Step 1: Write `requirements-dev.txt` and install it**

```
pytest
```

Run: `python -m pip install -r requirements-dev.txt`
Expected: pytest installs successfully.

- [ ] **Step 2: Write the failing tests**

`tests/test_pricing.py`:
```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_pricing.py -v`
Expected: `ModuleNotFoundError: No module named 'pricing'` (file doesn't exist yet).

- [ ] **Step 4: Write the implementation**

`addons/panel_cpq/pricing.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pricing.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add addons/panel_cpq/pricing.py tests/test_pricing.py requirements-dev.txt
git commit -m "Add pricing logic with unit tests"
git push
```

---

### Task 3: Module skeleton — manifest, security, empty package

**Files:**
- Create: `addons/panel_cpq/__init__.py`
- Create: `addons/panel_cpq/__manifest__.py`
- Create: `addons/panel_cpq/models/__init__.py`
- Create: `addons/panel_cpq/security/ir.model.access.csv` (empty header only for now — rows added in Tasks 4-5)

**Interfaces:**
- Produces: an installable (empty) Odoo module named "Panel CPQ Demo", proving the addons bind-mount and manifest are wired correctly before adding real models.

- [ ] **Step 1: Write `addons/panel_cpq/__manifest__.py`**

```python
{
    'name': 'Panel CPQ Demo',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Demo CPQ configurator for acrylic panel pricing, injecting a priced line into Sales quotations.',
    'author': 'Vence',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
```

- [ ] **Step 2: Write `addons/panel_cpq/__init__.py`**

```python
from . import models
```

- [ ] **Step 3: Write `addons/panel_cpq/models/__init__.py`**

```python
```
(empty for now — populated in Tasks 4 and 5)

- [ ] **Step 4: Write `addons/panel_cpq/security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```
(header only — rows added in Tasks 4 and 5)

- [ ] **Step 5: Restart Odoo and verify the module is detected**

Run: `docker compose restart web`
Expected: `docker compose logs web --tail=50` shows Odoo finishing startup with no Python tracebacks.

Using a browser, log into `http://localhost:8069` as the admin created in Task 1. Go to Apps, remove the default "Apps" filter (click into the search bar and remove any filters), search for "Panel CPQ Demo". Click "Activate the developer mode" first if the module doesn't show (Settings → General Settings → scroll to bottom → Activate the developer mode), then update the apps list (Apps → the ⋮ menu → "Update Apps List"), then search again.

Expected: "Panel CPQ Demo" appears in the Apps list, uninstalled. Click "Activate" / install it. Expected: installs with no error banner.

- [ ] **Step 6: Commit**

```bash
git add addons/panel_cpq/__init__.py addons/panel_cpq/__manifest__.py addons/panel_cpq/models/__init__.py addons/panel_cpq/security/ir.model.access.csv
git commit -m "Add panel_cpq module skeleton"
git push
```

---

### Task 4: `panel.cpq.instance` model, sequence, and views

**Files:**
- Create: `addons/panel_cpq/models/panel_cpq_instance.py`
- Modify: `addons/panel_cpq/models/__init__.py`
- Create: `addons/panel_cpq/data/panel_cpq_sequence.xml`
- Create: `addons/panel_cpq/views/panel_cpq_instance_views.xml`
- Modify: `addons/panel_cpq/security/ir.model.access.csv`
- Modify: `addons/panel_cpq/__manifest__.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (models/sequence are new).
- Produces: model `panel.cpq.instance` with fields `name` (Char, auto-numbered `CPQ-00001` style), `material` (Selection: `clear`/`frosted`/`black`), `length_in`, `width_in`, `thickness_mm` (Float), `price` (Float), `description` (Char), `sale_order_line_id` (Many2one `sale.order.line`). Consumed by `panel_cpq_wizard.py` in Task 5, which calls `self.env['panel.cpq.instance'].create({...})`.

- [ ] **Step 1: Write `addons/panel_cpq/models/panel_cpq_instance.py`**

```python
from odoo import api, fields, models


class PanelCpqInstance(models.Model):
    _name = 'panel.cpq.instance'
    _description = 'Panel CPQ Instance'
    _order = 'id desc'

    name = fields.Char(string='Instance ID', required=True, copy=False, readonly=True, default='New')
    material = fields.Selection(
        selection=[('clear', 'Clear'), ('frosted', 'Frosted'), ('black', 'Black')],
        string='Material', required=True,
    )
    length_in = fields.Float(string='Length (in)', required=True)
    width_in = fields.Float(string='Width (in)', required=True)
    thickness_mm = fields.Float(string='Thickness (mm)', required=True)
    price = fields.Float(string='Price', required=True)
    description = fields.Char(string='Description', required=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Quotation Line', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('panel.cpq.instance') or 'New'
        return super().create(vals_list)
```

- [ ] **Step 2: Modify `addons/panel_cpq/models/__init__.py`**

```python
from . import panel_cpq_instance
```

- [ ] **Step 3: Write `addons/panel_cpq/data/panel_cpq_sequence.xml`**

```xml
<odoo>
    <data noupdate="1">
        <record id="seq_panel_cpq_instance" model="ir.sequence">
            <field name="name">Panel CPQ Instance</field>
            <field name="code">panel.cpq.instance</field>
            <field name="prefix">CPQ-</field>
            <field name="padding">5</field>
            <field name="number_increment">1</field>
        </record>
    </data>
</odoo>
```

- [ ] **Step 4: Write `addons/panel_cpq/views/panel_cpq_instance_views.xml`**

```xml
<odoo>
    <record id="view_panel_cpq_instance_list" model="ir.ui.view">
        <field name="name">panel.cpq.instance.list</field>
        <field name="model">panel.cpq.instance</field>
        <field name="arch" type="xml">
            <list>
                <field name="name"/>
                <field name="material"/>
                <field name="length_in"/>
                <field name="width_in"/>
                <field name="thickness_mm"/>
                <field name="price"/>
                <field name="sale_order_line_id"/>
            </list>
        </field>
    </record>

    <record id="view_panel_cpq_instance_form" model="ir.ui.view">
        <field name="name">panel.cpq.instance.form</field>
        <field name="model">panel.cpq.instance</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <field name="name" readonly="1"/>
                        <field name="material"/>
                        <field name="length_in"/>
                        <field name="width_in"/>
                        <field name="thickness_mm"/>
                        <field name="price"/>
                        <field name="description"/>
                        <field name="sale_order_line_id"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_panel_cpq_instance" model="ir.actions.act_window">
        <field name="name">Panel CPQ Instances</field>
        <field name="res_model">panel.cpq.instance</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem id="menu_panel_cpq_instance"
              name="Panel CPQ Instances"
              parent="sale.menu_sale_config"
              action="action_panel_cpq_instance"
              sequence="100"/>
</odoo>
```

- [ ] **Step 5: Modify `addons/panel_cpq/security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_panel_cpq_instance_sale_user,panel.cpq.instance.sale.user,model_panel_cpq_instance,sales_team.group_sale_salesman,1,1,1,1
```

- [ ] **Step 6: Modify `addons/panel_cpq/__manifest__.py`**

Update the `data` list to:
```python
    'data': [
        'security/ir.model.access.csv',
        'data/panel_cpq_sequence.xml',
        'views/panel_cpq_instance_views.xml',
    ],
```

- [ ] **Step 7: Upgrade the module and verify sequential naming**

Run: `docker compose restart web`

Using the browser: go to the Sales app → Configuration → "Panel CPQ Instances" (the new menu). Click New. Fill in Material = Clear, Length = 10, Width = 10, Thickness = 5, Price = 40.00, Description = "test". Save.

Expected: after save, the `Instance ID` (`name`) field shows `CPQ-00001`. Create a second record the same way and confirm it shows `CPQ-00002`.

Take a screenshot of the saved record showing the `CPQ-00001` name and save it to `docs/screenshots/instance-sequence.png`.

- [ ] **Step 8: Commit**

```bash
git add addons/panel_cpq/models/panel_cpq_instance.py addons/panel_cpq/models/__init__.py addons/panel_cpq/data/panel_cpq_sequence.xml addons/panel_cpq/views/panel_cpq_instance_views.xml addons/panel_cpq/security/ir.model.access.csv addons/panel_cpq/__manifest__.py docs/screenshots/instance-sequence.png
git commit -m "Add panel.cpq.instance model with sequence-based instance IDs"
git push
```

---

### Task 5: Wizard, generic line product, sale.order button, and end-to-end flow

**Files:**
- Create: `addons/panel_cpq/models/panel_cpq_wizard.py`
- Create: `addons/panel_cpq/models/sale_order.py`
- Modify: `addons/panel_cpq/models/__init__.py`
- Create: `addons/panel_cpq/data/panel_cpq_product_data.xml`
- Create: `addons/panel_cpq/views/panel_cpq_wizard_views.xml`
- Create: `addons/panel_cpq/views/sale_order_views.xml`
- Modify: `addons/panel_cpq/security/ir.model.access.csv`
- Modify: `addons/panel_cpq/__manifest__.py`

**Interfaces:**
- Consumes: `compute_price`/`format_description` from `pricing.py` (Task 2), `panel.cpq.instance` model (Task 4).
- Produces: the full user-facing flow — a button on `sale.order` that opens `panel.cpq.wizard`, which creates one `panel.cpq.instance` and one `sale.order.line` per confirm.

- [ ] **Step 1: Write `addons/panel_cpq/data/panel_cpq_product_data.xml`**

A generic placeholder product so injected lines behave like normal Odoo sales lines for invoicing/reporting (a data record, not a schema change):

```xml
<odoo>
    <data noupdate="1">
        <record id="product_panel_cpq_line" model="product.product">
            <field name="name">Custom Acrylic Panel (CPQ)</field>
            <field name="type">service</field>
            <field name="invoice_policy">order</field>
            <field name="sale_ok">True</field>
            <field name="purchase_ok">False</field>
            <field name="list_price">0.0</field>
        </record>
    </data>
</odoo>
```

- [ ] **Step 2: Write `addons/panel_cpq/models/panel_cpq_wizard.py`**

```python
from odoo import api, fields, models
from odoo.exceptions import UserError

from ..pricing import compute_price, format_description


class PanelCpqWizard(models.TransientModel):
    _name = 'panel.cpq.wizard'
    _description = 'Panel CPQ Wizard'

    sale_order_id = fields.Many2one('sale.order', string='Quotation', required=True)
    material = fields.Selection(
        selection=[('clear', 'Clear'), ('frosted', 'Frosted'), ('black', 'Black')],
        string='Material', required=True, default='clear',
    )
    length_in = fields.Float(string='Length (in)', required=True)
    width_in = fields.Float(string='Width (in)', required=True)
    thickness_mm = fields.Float(string='Thickness (mm)', required=True)
    price = fields.Float(string='Price', compute='_compute_price_and_description', readonly=True)
    description = fields.Char(string='Description', compute='_compute_price_and_description', readonly=True)

    @api.depends('material', 'length_in', 'width_in', 'thickness_mm')
    def _compute_price_and_description(self):
        for wizard in self:
            if wizard.length_in > 0 and wizard.width_in > 0 and wizard.thickness_mm > 0:
                wizard.price = compute_price(wizard.length_in, wizard.width_in, wizard.thickness_mm, wizard.material)
                wizard.description = format_description(
                    wizard.material, wizard.thickness_mm, wizard.length_in, wizard.width_in, 'pending',
                )
            else:
                wizard.price = 0.0
                wizard.description = ''

    def action_add_to_quote(self):
        self.ensure_one()
        if self.length_in <= 0 or self.width_in <= 0 or self.thickness_mm <= 0:
            raise UserError("Length, width, and thickness must all be greater than zero.")

        instance = self.env['panel.cpq.instance'].create({
            'material': self.material,
            'length_in': self.length_in,
            'width_in': self.width_in,
            'thickness_mm': self.thickness_mm,
            'price': self.price,
            'description': self.description,
        })

        line = self.env['sale.order.line'].create({
            'order_id': self.sale_order_id.id,
            'product_id': self.env.ref('panel_cpq.product_panel_cpq_line').id,
            'name': format_description(
                self.material, self.thickness_mm, self.length_in, self.width_in, instance.name,
            ),
            'product_uom_qty': 1,
            'price_unit': self.price,
        })
        instance.write({
            'sale_order_line_id': line.id,
            'description': line.name,
        })
        return {'type': 'ir.actions.act_window_close'}
```

- [ ] **Step 3: Write `addons/panel_cpq/models/sale_order.py`**

```python
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_panel_cpq_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Panel (CPQ)',
            'res_model': 'panel.cpq.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }
```

- [ ] **Step 4: Modify `addons/panel_cpq/models/__init__.py`**

```python
from . import panel_cpq_instance
from . import panel_cpq_wizard
from . import sale_order
```

- [ ] **Step 5: Write `addons/panel_cpq/views/panel_cpq_wizard_views.xml`**

```xml
<odoo>
    <record id="view_panel_cpq_wizard_form" model="ir.ui.view">
        <field name="name">panel.cpq.wizard.form</field>
        <field name="model">panel.cpq.wizard</field>
        <field name="arch" type="xml">
            <form string="Add Panel (CPQ)">
                <group>
                    <field name="sale_order_id" invisible="1"/>
                    <field name="material"/>
                    <field name="length_in"/>
                    <field name="width_in"/>
                    <field name="thickness_mm"/>
                </group>
                <group>
                    <field name="price"/>
                    <field name="description"/>
                </group>
                <footer>
                    <button name="action_add_to_quote" type="object" string="Add to Quote" class="btn-primary"/>
                    <button string="Cancel" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
```

- [ ] **Step 6: Write `addons/panel_cpq/views/sale_order_views.xml`**

```xml
<odoo>
    <record id="view_order_form_inherit_panel_cpq" model="ir.ui.view">
        <field name="name">sale.order.form.inherit.panel.cpq</field>
        <field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header" position="inside">
                <button name="action_open_panel_cpq_wizard"
                        type="object"
                        string="Add Panel (CPQ)"
                        class="btn-secondary"
                        invisible="state not in ('draft', 'sent')"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 7: Modify `addons/panel_cpq/security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_panel_cpq_instance_sale_user,panel.cpq.instance.sale.user,model_panel_cpq_instance,sales_team.group_sale_salesman,1,1,1,1
access_panel_cpq_wizard_sale_user,panel.cpq.wizard.sale.user,model_panel_cpq_wizard,sales_team.group_sale_salesman,1,1,1,1
```

- [ ] **Step 8: Modify `addons/panel_cpq/__manifest__.py`**

Update the `data` list to:
```python
    'data': [
        'security/ir.model.access.csv',
        'data/panel_cpq_sequence.xml',
        'data/panel_cpq_product_data.xml',
        'views/panel_cpq_instance_views.xml',
        'views/panel_cpq_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
```

- [ ] **Step 9: Upgrade the module**

Run: `docker compose restart web`
Expected: `docker compose logs web --tail=50` shows no Python tracebacks and the module data loads cleanly. If it doesn't pick up automatically, go to Apps → find "Panel CPQ Demo" → Upgrade.

- [ ] **Step 10: End-to-end manual verification — scenario 1 (normal size, above minimum charge)**

Using the browser: Sales app → New quotation → pick or create any customer → click the new "Add Panel (CPQ)" button in the header. In the wizard: Material = Clear, Length = 24, Width = 18, Thickness = 6.

Expected: the wizard's `price` field live-updates to `64.5` and `description` shows `Acrylic Panel — Clear, 6.0mm, 24.0in × 18.0in [pending]` as soon as all three dimension fields are filled.

Click "Add to Quote". Expected: wizard closes, a new order line appears on the quotation with description `Acrylic Panel — Clear, 6.0mm, 24.0in × 18.0in [CPQ-00003]` (or whatever the next sequence number is), quantity 1, unit price 64.50.

Go to Sales → Configuration → Panel CPQ Instances and confirm a matching instance record exists with the same dimensions/price and its `Quotation Line` field pointing at the new line.

Take a screenshot of the quotation with the new line and save it to `docs/screenshots/quote-line-normal.png`.

- [ ] **Step 11: End-to-end manual verification — scenario 2 (hits the minimum charge floor)**

On the same or a new quotation, open the wizard again: Material = Frosted, Length = 4, Width = 4, Thickness = 3.

Expected: `price` live-updates to `35.0` (the minimum charge, since the raw formula computes well below it). Click "Add to Quote" and confirm the resulting line's unit price is exactly `35.00`.

Take a screenshot and save it to `docs/screenshots/quote-line-minimum-floor.png`.

- [ ] **Step 12: Commit**

```bash
git add addons/panel_cpq/data/panel_cpq_product_data.xml addons/panel_cpq/models/panel_cpq_wizard.py addons/panel_cpq/models/sale_order.py addons/panel_cpq/models/__init__.py addons/panel_cpq/views/panel_cpq_wizard_views.xml addons/panel_cpq/views/sale_order_views.xml addons/panel_cpq/security/ir.model.access.csv addons/panel_cpq/__manifest__.py docs/screenshots/quote-line-normal.png docs/screenshots/quote-line-minimum-floor.png
git commit -m "Add CPQ wizard and sale.order button wiring the full pricing flow"
git push
```

---

### Task 6: README and final polish

**Files:**
- Create: `README.md`

**Interfaces:**
- Produces: the top-level portfolio document a client would read first when clicking through from a Freelancer proposal.

- [ ] **Step 1: Write `README.md`**

```markdown
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

## Screenshots

![Sequential instance IDs](docs/screenshots/instance-sequence.png)
![Quotation line — normal size](docs/screenshots/quote-line-normal.png)
![Quotation line — minimum charge floor](docs/screenshots/quote-line-minimum-floor.png)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Add README with setup instructions and screenshots"
git push
```
