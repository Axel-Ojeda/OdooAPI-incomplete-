from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_sistek_qty(self):
        """Cantidad disponible en ubicación Sistek (supplier/external)."""
        ICP = self.env["ir.config_parameter"].sudo()
        loc_id = ICP.get_param("api.inventory.sistek_location_id")
        if not loc_id:
            return 0.0

        location = self.env["stock.location"].sudo().browse(int(loc_id))
        if not location.exists():
            return 0.0

        self.ensure_one()
        Quant = self.env["stock.quant"].sudo()
        return Quant._get_available_quantity(self, location)

    def _get_combination_info(
        self, combination=False, product_id=False, add_qty=1, pricelist=False,
        parent_combination=False, only_template=False
    ):
        info = super()._get_combination_info(
            combination=combination,
            product_id=product_id,
            add_qty=add_qty,
            pricelist=pricelist,
            parent_combination=parent_combination,
            only_template=only_template,
        )

        # Solo modificar en contexto website
        if not self.env.context.get("website_id"):
            return info

        template = self.product_tmpl_id
        if not template.x_sistek_sync_enabled:
            return info

        # Sumamos stock Sistek
        sistek_qty = self._get_sistek_qty()
        if sistek_qty > 0:
            info["free_qty"] = info.get("free_qty", 0) + sistek_qty
            info["available_qty"] = info.get("available_qty", 0) + sistek_qty
            info["has_stock"] = True

        return info
