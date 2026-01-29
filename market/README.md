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


-Sync Sistek Products -- res.users --  result = env["sistek.stock.map"].sync_all_active(refresh_catalog_first=True)

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

- Sync Sistek API -- (Stock Sync) -- 
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

3. Make menus, these are temp though

-Debug API Inventory -- Settings/Technical -- 99 -- Action: ir.action.act_window / API Inventory Snapshot

-Debug API Inventory -- Settings/Technical -- 99 -- Action: ir.action.act_window / API Inventory Items

4. Scheduled Actions:

--Sync Sistek API (Stock Sync) --

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

-- API Inventory Snapshot -- Snapshot
-- Apply Sistek Stock to Marked Products -- selected product