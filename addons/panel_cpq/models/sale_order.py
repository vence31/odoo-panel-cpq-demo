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
