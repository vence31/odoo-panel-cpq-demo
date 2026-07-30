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
