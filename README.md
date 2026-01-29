Lot's of things to do starting by

1. Make a System parameter keyed: api.inventory.sistek_location_id valued: 165 (That is the number of the warehouse in thew URL) 

2. Check the Server Actions:

-Sync Catálogo Sistek -- res.users --
```
result = env["sistek.marketplace.client"].sudo().sync_products_basic()

action = {
  "type": "ir.actions.client",
  "tag": "display_notification",
  "params": {
    "title": "Sistek Catálogo",
    "message": (
      f"✅ Catálogo actualizado\n"
      f"Creados: {result.get('created', 0)}\n"
      f"Actualizados: {result.get('updated', 0)}\n"
      f"Total: {result.get('total', 0)}"
    ),
    "type": "success",
    "sticky": False,
  }
}
```


-Sync Sistek Products -- res.users --  
```
result = env["sistek.stock.map"].sync_all_active(refresh_catalog_first=True)

action = {
    "type": "ir.actions.client",
    "tag": "display_notification",
    "params": {
        "title": "Sistek Stock Sync",
        "message": (
            f"✅ Sync OK\n"
            f"Vinculaciones: {result['mappings']}\n"
            f"Actualizados: {result['updated']}\n"
            f"Saltados/Error: {result['skipped']}"
        ),
        "type": "success",
        "sticky": False,
    }
}
```
- Sync Sistek API -- (Stock Sync) -- 
```
result = env["sistek.stock.map"].sync_all_active(refresh_catalog_first=True)

action = {
    "type": "ir.actions.client",
    "tag": "display_notification",
    "params": {
        "title": "Sistek Stock Sync",
        "message": (
            f"✅ Sync OK\n"
            f"Vinculaciones: {result['mappings']}\n"
            f"Actualizados: {result['updated']}\n"
            f"Saltados/Error: {result['skipped']}"
        ),
        "type": "success",
        "sticky": False,
    }
}
```
3. Make menus, these are temp though

-Debug API Inventory -- Settings/Technical -- 99 -- Action: ir.action.act_window / API Inventory Snapshot

-Debug API Inventory -- Settings/Technical -- 99 -- Action: ir.action.act_window / API Inventory Items

4. Scheduled Actions:

--Sync Sistek API (Stock Sync) --
```
result = env["sistek.stock.map"].sync_all_active(refresh_catalog_first=True)

action = {
    "type": "ir.actions.client",
    "tag": "display_notification",
    "params": {
        "title": "Sistek Stock Sync",
        "message": (
            f"✅ Sync OK\n"
            f"Vinculaciones: {result['mappings']}\n"
            f"Actualizados: {result['updated']}\n"
            f"Saltados/Error: {result['skipped']}"
        ),
        "type": "success",
        "sticky": False,
    }
}
```
# Odoo.sh editor

## *data* Directory

**data** has the API Inventory Snapshot and Apply Sistek Stock to Marked Products in it's XMLs, meaning we don't need to genereate said schedule actions.

## */views* Directory

*views/menu.xml*
- Menú principal “Sistek” y submenú “Catálogo” (si lo usas).
- Base para colgar acciones.

*views/sistek_operations_menu.xml*
Menú “Sistek → Operaciones” con “botones” que ejecutan:
- Snapshot (Fase 1)
- Apply stock (Fase 2)
  (y/o sync catálogo si lo mantienes)

*views/product_template_views.xml*
Hereda el formulario de ```product.template```:
- añade pestaña “Sistek”
- muestra checkbox ```x_sistek_sync_enabled```
- muestra campo ```x_sistek_item_code``` (y opcionalmente partnumber)

## */models*

*models/api_client.py*
Cliente HTTP hacia la API de Sistek:
- hace login y obtiene token
- llama ```GET /Productos```
- maneja refresh del token si expira

models/api_inventory_snapshot.py
Modelo ```api.inventory.snapshot```:
- registra cada ejecución de snapshot (estado: running/done/failed)
- guarda métricas: total items, upserts, duración, error
- método ```run_snapshot()``` hace 1 llamada al API y actualiza el catálogo sombra

*models/api_inventory_item.py*
Modelo ```api.inventory.item``` (catálogo sombra / snapshot cache):
- 1 registro por item_code
- guarda ```qty_available```, price, etc.
- ```raw_json``` activable/desactivable por parámetro
- método ```upsert_from_api_payload()``` (dedup + upsert)

*models/api_inventory_apply_sistek.py*
“Fase 2”: aplica stock a productos seleccionados en Odoo:
- busca ```product.template``` con ```x_sistek_sync_enabled = True```
- usa ```x_sistek_item_code``` (manual) o fallback al partnumber si lo dejas
- busca en ```api.inventory.item```
- escribe cantidad idempotente en ubicación configurada (```api.inventory.sistek_location_id```)

*models/product_template_ext.py*
Extiende product.template con campos de control:
- ```x_sistek_sync_enabled``` (checkbox)
- ```x_sistek_item_code``` (ItemCode manual para matching)
  (tu ```x_product_partnumber``` ya existe, no lo redefinimos)

*models/product_product_website_ext.py* (Fase 3 eCommerce)
Extiende ```product.product``` para la tienda:
- suma disponibilidad “comercial” para website
- modifica ```free_qty/available_qty``` en ```_get_combination_info```
- así la tienda puede considerar stock Sistek sin mentir inventario interno


## Parameters

En Ajustes → Técnico → Parámetros del sistema:

- sistek.base_url
- sistek.username
- sistek.password
- sistek.token_access (se guarda solo)
- api.inventory.store_raw_json = 1/0
- api.inventory.sistek_location_id = ID ubicación destino (la que ya configuraste) 