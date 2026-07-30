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
