from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_sistek_sync_enabled = fields.Boolean(
        string="Sincronizar stock Sistek",
        default=False,
        help="Si está activo, este producto tomará stock desde el snapshot del API y lo escribirá en la ubicación Sistek.",
    )

    x_sistek_item_code = fields.Char(
        string="Sistek ItemCode",
        index=True,
        help="ItemCode exacto del API de Sistek a usar para sincronizar stock (manual).",
    )
