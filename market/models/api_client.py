import logging
import requests
from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SistekMarketplaceClient(models.AbstractModel):
    _name = "sistek.marketplace.client"
    _description = "Sistek Marketplace API Client"

    # ---- Helpers de configuración ----
    @api.model
    def _get_param(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    @api.model
    def _set_param(self, key, value):
        self.env["ir.config_parameter"].sudo().set_param(key, value)

    @api.model
    def _base_url(self):
        return (self._get_param("sistek.base_url") or "https://marketplace.sistek.cl").rstrip("/")

    # ---- Token management ----
    @api.model
    def get_token(self, force_refresh=False):
        token = self._get_param("sistek.token_access")

        # Validación mínima
        if token and not force_refresh:
            return token

        return self.login_and_store_token()

    @api.model
    def login_and_store_token(self):
        username = self._get_param("sistek.username")
        password = self._get_param("sistek.password")

        if not username or not password:
            raise UserError(_(
                "Faltan credenciales del API. Configura sistek.username y sistek.password en Parámetros del Sistema."
            ))

        url = f"{self._base_url()}/login/autenticate"

        try:
            # requests.post(..., data=...) -> x-www-form-urlencoded / form-data equivalente
            resp = requests.post(url, data={"username": username, "password": password}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            _logger.exception("Error llamando a login Sistek")
            raise UserError(_("No se pudo conectar al API de Sistek: %s") % str(e))
        except ValueError:
            raise UserError(_("Respuesta inválida del API (no es JSON)."))

        token = data.get("token_access")
        expired_at = data.get("expired_at")  # puede venir o no

        if not token:
            raise UserError(_("Login OK pero no vino 'token_access' en la respuesta."))

        self._set_param("sistek.token_access", token)
        if expired_at:
            self._set_param("sistek.token_expired_at", expired_at)

        _logger.info("Token Sistek almacenado correctamente.")
        return token

    # ---- Llamadas autenticadas ----
    @api.model
    def _auth_headers(self):
        token = self.get_token()
        return {"Authorization": f"Bearer {token}"}

    @api.model
    def test_products_ping(self):
        """
        Método de prueba: GET /Productos. Si el token expiró, reintenta 1 vez forzando refresh.
        """
        url = f"{self._base_url()}/Productos"
        try:
            resp = requests.get(url, headers=self._auth_headers(), timeout=30)
            if resp.status_code == 401:
                token = self.get_token(force_refresh=True)
                resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)

            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            _logger.exception("Error consultando /Productos")
            raise UserError(_("Fallo consultando /Productos: %s") % str(e))

    @api.model
    def sync_products_basic(self):
        """
        Sincroniza el catálogo Sistek completo hacia el modelo sistek.product (catálogo externo).
        """
        products = self.test_products_ping()
        result = self.env["sistek.product"].sudo().upsert_from_api_payload(products)
        return result
