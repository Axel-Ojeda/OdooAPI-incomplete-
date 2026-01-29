from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SistekLinkWizard(models.TransientModel):
    _name = "sistek.link.wizard"
    _description = "Wizard: Vincular producto Sistek con producto Odoo"

    sistek_product_id = fields.Many2one("sistek.product", required=True, readonly=True)

    product_id = fields.Many2one("product.product", required=True)
    location_id = fields.Many2one(
        "stock.location",
        required=True,
        domain=[("usage", "=", "internal")],
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Sistek product desde contexto
        sistek_id = self.env.context.get("default_sistek_product_id")
        if not sistek_id:
            raise UserError(_("No se encontró el producto Sistek en el contexto del wizard."))
        res["sistek_product_id"] = sistek_id

        # Default location desde System Parameter
        loc_id = self.env["ir.config_parameter"].sudo().get_param("sistek.stock_location_id")
        if loc_id:
            try:
                res["location_id"] = int(loc_id)
            except Exception:
                pass

        return res

    def action_confirm_link(self):
        self.ensure_one()

        Map = self.env["sistek.stock.map"].sudo()

        # Si ya existe mapping para este producto Sistek, actualizamos
        existing = Map.search([("sistek_product_id", "=", self.sistek_product_id.id)], limit=1)

        vals = {
            "sistek_product_id": self.sistek_product_id.id,
            "product_id": self.product_id.id,
            "location_id": self.location_id.id,
            "active": True,
        }

        if existing:
            existing.write(vals)
        else:
            Map.create(vals)

        # Notificación sin rollback
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Vinculación Sistek",
                "message": "✅ Producto vinculado correctamente.",
                "type": "success",
                "sticky": False,
            },
        }
