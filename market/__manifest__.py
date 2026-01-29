{
    "name": "ADAPTOR Sistek Marketplace",
    "version": "17.0.1.0.0",
    "category": "Inventory/Integration",
    "summary": "Conector con proveedor Sistek para sincronización de catálogo y stock",
    "description": """
Integración con API de proveedor Sistek para ADAPTOR Chile.

Funcionalidades:
- Sincronización de catálogo de productos Sistek
- Mapeo de productos Sistek a productos Odoo
- Sincronización de stock a ubicación interna
- Wizard para vinculación masiva de productos

Historial de versiones:
17.0.1.0.0 - Implementación inicial
    """,
    "author": "ADAPTOR Chile SpA",
    "website": "https://www.adaptor.cl",
    "depends": ["base", "product", "stock", "website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/sistek_link_wizard_views.xml",
        "views/sistek_stock_map_views.xml",
        "views/sistek_product_views.xml",
        "views/menu.xml",
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/product_template_views.xml",
        "views/sistek_operations_menu.xml",
        "data/ir_cron_phase2.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
