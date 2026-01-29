from odoo import api, models, _
from odoo.exceptions import UserError


class ApiInventoryApplySistek(models.AbstractModel):
    _name = "api.inventory.apply.sistek"
    _description = "Apply Sistek API snapshot stock to selected products"

    @api.model
    def _get_sistek_location(self):
        ICP = self.env["ir.config_parameter"].sudo()
        loc_id = ICP.get_param("api.inventory.sistek_location_id")
        if not loc_id:
            raise UserError(_("Falta configurar api.inventory.sistek_location_id con el ID de la ubicación Sistek."))

        location = self.env["stock.location"].sudo().browse(int(loc_id))
        if not location.exists():
            raise UserError(_("La ubicación Sistek configurada no existe."))

        if location.usage not in ("supplier", "internal"):
            raise UserError(_("La ubicación Sistek debe ser 'supplier' o 'internal'."))
        return location

    @api.model
    def apply(self):
        location = self._get_sistek_location()

        ProductT = self.env["product.template"].sudo()
        templates = ProductT.search([("x_sistek_sync_enabled", "=", True)])

        # 1) No hay productos marcados
        if not templates:
            return {
                "templates": 0, "matched": 0, "updated": 0,
                "missing_in_snapshot": 0, "missing_code": 0,
                "debug": [f"0 templates con x_sistek_sync_enabled=True"]
            }

        # 2) Determinar código por template
        tmpl_code = {}
        missing_code = 0
        codes = []

        for t in templates:
            code = (t.x_sistek_item_code or "").strip() or (t.x_product_partnumber or "").strip()
            if not code:
                missing_code += 1
                continue
            tmpl_code[t.id] = code
            codes.append(code)

        codes = list(set(codes))

        # 3) Buscar en snapshot
        ApiItem = self.env["api.inventory.item"].sudo()
        api_items = ApiItem.search([("item_code", "in", codes)])
        api_by_code = {i.item_code: i for i in api_items}

        Quant = self.env["stock.quant"].sudo()

        matched = 0
        updated = 0
        missing_in_snapshot = 0

        debug_lines = []
        debug_limit = 5  # muestra hasta 5 ejemplos

        for tmpl in templates:
            code = tmpl_code.get(tmpl.id)
            if not code:
                if len(debug_lines) < debug_limit:
                    debug_lines.append(f"[{tmpl.id}] {tmpl.display_name}: SIN CODIGO (x_sistek_item_code/partnumber)")
                continue

            api_item = api_by_code.get(code)
            if api_item:
                matched += 1
                target_qty = float(api_item.qty_available or 0.0)
            else:
                missing_in_snapshot += 1
                target_qty = 0.0

            prod = tmpl.product_variant_id
            current_qty = Quant._get_available_quantity(prod, location)
            delta = target_qty - current_qty

            if len(debug_lines) < debug_limit:
                debug_lines.append(
                    f"[{tmpl.id}] code={code} target={target_qty} current={current_qty} delta={delta}"
                )

            if abs(delta) > 0.0001:
                Quant._update_available_quantity(prod, location, delta)
                updated += 1

        return {
            "templates": len(templates),
            "matched": matched,
            "updated": updated,
            "missing_in_snapshot": missing_in_snapshot,
            "missing_code": missing_code,
            "debug": debug_lines,
            "location": f"{location.display_name} (usage={location.usage}, id={location.id})"
        }
