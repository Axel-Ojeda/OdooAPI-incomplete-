import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class SistekStockMap(models.Model):
    _name = "sistek.stock.map"
    _description = "Sistek ↔ Odoo Product Mapping (Stock Sync)"
    # NO ponemos _rec_name para evitar que el registry muera si alguien renombra campos

    active = fields.Boolean(default=True)

    sistek_product_id = fields.Many2one(
        "sistek.product", required=True, ondelete="cascade", index=True
    )
    product_id = fields.Many2one(
        "product.product", required=True, ondelete="restrict", index=True
    )
    location_id = fields.Many2one(
        "stock.location",
        required=True,
        domain=[("usage", "=", "internal")],
        help="Ubicación interna donde se reflejará el stock del API (ej: Bodega Sistek / Stock).",
    )

    last_sync = fields.Datetime()

    # Campo NAME real (así el modelo siempre tiene un nombre visible)
    name = fields.Char(compute="_compute_name", store=True)

    _sql_constraints = [
        ("uniq_sistek_product", "unique(sistek_product_id)", "Este producto Sistek ya está vinculado."),
        ("uniq_odoo_product", "unique(product_id)", "Este producto Odoo ya está vinculado a otro producto Sistek."),
    ]

    @api.depends("sistek_product_id.item_code", "product_id.name")
    def _compute_name(self):
        for r in self:
            code = r.sistek_product_id.item_code or ""
            pname = r.product_id.name or ""
            r.name = f"[{code}] → {pname}".strip()

    @api.constrains("location_id")
    def _check_location_internal(self):
        for r in self:
            if r.location_id and r.location_id.usage != "internal":
                raise ValidationError(_("La ubicación debe ser de tipo 'internal'."))

    # --------- SYNC METHODS (los dejamos aquí también) ---------
    def action_sync_stock(self):
        """
        Sincroniza stock para ESTE mapping.
        Usa sistek_product_id.stock y sobrescribe en location_id para product_id.
        """
        self.ensure_one()

        if not self.active:
            return False

        if not self.sistek_product_id or not self.product_id or not self.location_id:
            raise UserError(_("Mapping incompleto: falta producto Sistek, producto Odoo o ubicación."))

        Quant = self.env["stock.quant"].sudo()

        target_qty = int(self.sistek_product_id.stock or 0)
        current_qty = Quant._get_available_quantity(self.product_id, self.location_id)
        delta = target_qty - current_qty

        if delta:
            Quant._update_available_quantity(self.product_id, self.location_id, delta)

        self.last_sync = fields.Datetime.now()
        return True

    @api.model
    def sync_all_active(self, refresh_catalog_first=True):
        """
        Sincroniza stock para todos los mappings activos.
        """
        if refresh_catalog_first:
            self.env["sistek.marketplace.client"].sudo().sync_products_basic()

        mappings = self.search([("active", "=", True)])
        updated = 0
        skipped = 0

        for m in mappings:
            try:
                if m.action_sync_stock():
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                _logger.exception("Error sync mapping %s: %s", m.id, e)
                skipped += 1

        return {"mappings": len(mappings), "updated": updated, "skipped": skipped}
