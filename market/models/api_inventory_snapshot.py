import time
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ApiInventorySnapshot(models.Model):
    _name = "api.inventory.snapshot"
    _description = "API Inventory Snapshot"
    _order = "started_at desc"

    name = fields.Char(required=True)
    started_at = fields.Datetime(required=True, default=fields.Datetime.now)
    finished_at = fields.Datetime()
    state = fields.Selection(
        [("running", "Running"), ("done", "Done"), ("failed", "Failed")],
        required=True,
        default="running",
        index=True,
    )

    items_total = fields.Integer(default=0)
    items_upserted = fields.Integer(default=0)
    duration_ms = fields.Integer(default=0)
    error_message = fields.Text()

    @api.model
    def _is_running_recently(self, minutes=30):
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), minutes=minutes)
        return bool(self.search([("state", "=", "running"), ("started_at", ">=", cutoff)], limit=1))

    @api.model
    def run_snapshot(self):
        """
        Fase 1:
        - 1 llamada a API (/Productos)
        - upsert masivo en api.inventory.item
        - log en api.inventory.snapshot
        """
        # Lock lógico simple: evita superposición
        if self._is_running_recently(minutes=30):
            _logger.warning("Snapshot omitido: existe uno running reciente.")
            return {"skipped": True, "reason": "running_recent"}

        t0 = time.time()
        snap = self.create({
            "name": f"Snapshot {fields.Datetime.now()}",
            "started_at": fields.Datetime.now(),
            "state": "running",
        })

        try:
            client = self.env["sistek.marketplace.client"].sudo()
            payload = client.test_products_ping()  # GET /Productos

            if not isinstance(payload, list):
                raise UserError(_("Respuesta API inesperada: se esperaba lista."))

            snap.items_total = len(payload)

            res = self.env["api.inventory.item"].sudo().upsert_from_api_payload(
                payload_list=payload,
                snapshot_id=snap.id,
            )

            snap.items_upserted = res.get("upserted", 0)
            snap.state = "done"
            snap.finished_at = fields.Datetime.now()
            snap.duration_ms = int((time.time() - t0) * 1000)

            return {"skipped": False, "snapshot_id": snap.id, **res}

        except Exception as e:
            _logger.exception("Snapshot falló")
            snap.state = "failed"
            snap.finished_at = fields.Datetime.now()
            snap.duration_ms = int((time.time() - t0) * 1000)
            snap.error_message = str(e)
            # Re-lanzamos para visibilidad en logs/acciones
            raise
