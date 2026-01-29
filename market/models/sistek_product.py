import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)

try:
    from psycopg2 import IntegrityError
except Exception:
    IntegrityError = Exception


class SistekProduct(models.Model):
    _name = "sistek.product"
    _description = "Sistek Supplier Catalog Product"
    _rec_name = "name"

    active = fields.Boolean(default=True)

    item_code = fields.Char(required=True, index=True)
    item_name = fields.Char()
    name = fields.Char(compute="_compute_name", store=True)

    price = fields.Float()
    stock = fields.Integer()
    currency_code = fields.Char(size=8)

    brand = fields.Char()          # ItmsGrpNam
    family_code = fields.Char()    # Cod_SubFamilia
    family_name = fields.Char()    # Nom_SubFamilia / FrgnName

    last_sync = fields.Datetime()
    raw_json = fields.Text()

    _sql_constraints = [
        ("item_code_uniq", "unique(item_code)", "ItemCode debe ser único."),
    ]

    sync_enabled = fields.Boolean(string="Sync Stock", default=False)

    odoo_product_id = fields.Many2one(
        "product.product",
        string="Producto Odoo",
        help="Producto interno al que se vincula este ItemCode (usando x_studio_part_number si quieres validar).",
    )

    sistek_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación Sistek",
        domain=[("usage", "=", "internal")],
        help="Ubicación interna donde se reflejará el stock externo.",
    )

    @api.model
    def _default_sistek_location_id(self):
        loc_id = self.env["ir.config_parameter"].sudo().get_param("sistek.stock_location_id")
        return int(loc_id) if loc_id else False

    @api.model_create_multi
    def create(self, vals_list):
        # poner ubicación por defecto si no viene
        default_loc = self._default_sistek_location_id()
        for vals in vals_list:
            if not vals.get("sistek_location_id") and default_loc:
                vals["sistek_location_id"] = default_loc
        return super().create(vals_list)

    def write(self, vals):
        # poner ubicación por defecto si habilitan sync y no eligieron ubicación
        if "sync_enabled" in vals and vals["sync_enabled"]:
            if not vals.get("sistek_location_id"):
                default_loc = self._default_sistek_location_id()
                if default_loc and not self.sistek_location_id:
                    vals["sistek_location_id"] = default_loc
        return super().write(vals)

    @api.constrains("sync_enabled", "odoo_product_id")
    def _check_unique_odoo_product_mapping(self):
        # Evitar que 2 productos Sistek apunten al mismo producto Odoo (si están habilitados)
        for r in self:
            if r.sync_enabled and r.odoo_product_id:
                dup = self.search([
                    ("id", "!=", r.id),
                    ("sync_enabled", "=", True),
                    ("odoo_product_id", "=", r.odoo_product_id.id),
                ], limit=1)
                if dup:
                    raise UserError(_("El producto Odoo ya está vinculado a otro producto Sistek."))

    def sync_stock_to_location(self):
        """
        Sobrescribe stock en la ubicación Sistek para los productos seleccionados (sync_enabled).
        Usa el stock almacenado en el catálogo (campo stock) como fuente de verdad.
        """
        self.ensure_one()

        if not self.sync_enabled or not self.odoo_product_id:
            return False

        if not self.sistek_location_id:
            raise UserError(_("Falta Ubicación Sistek. Configura sistek.stock_location_id o asigna una ubicación."))

        Quant = self.env["stock.quant"].sudo()

        target_qty = int(self.stock or 0)
        current_qty = Quant._get_available_quantity(self.odoo_product_id, self.sistek_location_id)
        delta = target_qty - current_qty

        if delta:
            Quant._update_available_quantity(self.odoo_product_id, self.sistek_location_id, delta)

        self.last_sync = fields.Datetime.now()
        return True

    @api.model
    def sync_selected_stock(self):
        """
        Sincroniza stock para todos los SistekProducts marcados.
        """
        selected = self.search([
            ("sync_enabled", "=", True),
            ("odoo_product_id", "!=", False),
        ])

        updated = 0
        for r in selected:
            if r.sync_stock_to_location():
                updated += 1

        return {"selected": len(selected), "updated": updated}

    @api.depends("item_code", "item_name")
    def _compute_name(self):
        for r in self:
            r.name = f"[{r.item_code}] {r.item_name or ''}".strip()

    @api.model
    def upsert_from_api_payload(self, payload_list):
        if not isinstance(payload_list, list):
            raise UserError(_("Payload inesperado: se esperaba una lista."))

        # Deduplicar por ItemCode por si el API repite productos
        dedup = {}
        for p in payload_list:
            code = p.get("ItemCode")
            if code:
                dedup[code] = p  # el último gana
        payload_list = list(dedup.values())

        now = fields.Datetime.now()

        codes = list(dedup.keys())
        existing = self.search([("item_code", "in", codes)])
        by_code = {r.item_code: r for r in existing}

        created = 0
        updated = 0

        for p in payload_list:
            code = p.get("ItemCode")
            if not code:
                continue

            vals = {
                "item_code": code,
                "item_name": p.get("ItemName"),
                "price": p.get("Price") or 0.0,
                "stock": p.get("Stock") or 0,
                "currency_code": p.get("Currency"),
                "brand": p.get("ItmsGrpNam"),
                "family_code": p.get("Cod_SubFamilia"),
                "family_name": p.get("Nom_SubFamilia") or p.get("FrgnName"),
                "last_sync": now,
                "raw_json": json.dumps(p, ensure_ascii=False),
                "active": True,
            }

            rec = by_code.get(code)
            if rec:
                rec.write(vals)
                updated += 1
                continue

            # Crear con protección ante concurrencia / duplicados
            try:
                with mute_logger("odoo.sql_db"):
                    new_rec = self.create(vals)
                by_code[code] = new_rec
                created += 1
            except IntegrityError:
                rec2 = self.search([("item_code", "=", code)], limit=1)
                if rec2:
                    rec2.write(vals)
                    by_code[code] = rec2
                    updated += 1
                else:
                    raise

        return {"created": created, "updated": updated, "total": len(dedup)}
