import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApiInventoryItem(models.Model):
    _name = "api.inventory.item"
    _description = "API Inventory Item (Shadow Catalog)"
    _order = "item_code asc"
    _rec_name = "name"

    item_code = fields.Char(required=True, index=True)
    name = fields.Char(compute="_compute_name", store=True)

    qty_available = fields.Float(default=0.0)

    price = fields.Float()
    currency_code = fields.Char(size=8)

    item_name = fields.Char()
    brand = fields.Char()
    family_code = fields.Char()
    family_name = fields.Char()

    last_seen_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    last_snapshot_id = fields.Many2one("api.inventory.snapshot", required=True, ondelete="restrict", index=True)

    raw_json = fields.Text()

    _sql_constraints = [
        ("item_code_uniq", "unique(item_code)", "El item_code debe ser único."),
    ]

    @api.depends("item_code", "item_name")
    def _compute_name(self):
        for r in self:
            r.name = f"[{r.item_code}] {r.item_name or ''}".strip()

    @api.model
    def _store_raw_enabled(self):
        """
        Feature flag para almacenar raw_json durante desarrollo.
        Setea en ir.config_parameter:
          api.inventory.store_raw_json = "1" o "0"
        """
        val = self.env["ir.config_parameter"].sudo().get_param("api.inventory.store_raw_json", "1")
        return val == "1"

    @api.model
    def upsert_from_api_payload(self, payload_list, snapshot_id):
        """
        Upsert por item_code.
        payload_list: lista de dict (respuesta API)
        snapshot_id: api.inventory.snapshot
        """
        if not isinstance(payload_list, list):
            raise UserError(_("Payload inesperado: se esperaba lista."))

        snap = self.env["api.inventory.snapshot"].sudo().browse(snapshot_id)
        if not snap.exists():
            raise UserError(_("Snapshot no existe."))

        now = fields.Datetime.now()
        store_raw = self._store_raw_enabled()

        # Dedup por ItemCode (si API repite)
        dedup = {}
        for p in payload_list:
            code = p.get("ItemCode")
            if code:
                dedup[code] = p
        items = list(dedup.values())

        codes = list(dedup.keys())
        existing = self.search([("item_code", "in", codes)])
        by_code = {r.item_code: r for r in existing}

        created = 0
        updated = 0

        for p in items:
            code = p.get("ItemCode")
            if not code:
                continue

            vals = {
                "item_code": code,
                "qty_available": float(p.get("Stock") or 0.0),
                "price": float(p.get("Price") or 0.0),
                "currency_code": p.get("Currency"),
                "item_name": p.get("ItemName"),
                "brand": p.get("ItmsGrpNam"),
                "family_code": p.get("Cod_SubFamilia"),
                "family_name": p.get("Nom_SubFamilia") or p.get("FrgnName"),
                "last_seen_at": now,
                "last_snapshot_id": snap.id,
            }
            if store_raw:
                vals["raw_json"] = json.dumps(p, ensure_ascii=False)

            rec = by_code.get(code)
            if rec:
                rec.write(vals)
                updated += 1
            else:
                self.create(vals)
                created += 1

        return {"upserted": created + updated, "created": created, "updated": updated, "total": len(dedup)}
