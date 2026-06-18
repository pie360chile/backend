# Tablas legacy / candidatas a eliminación

Auditoría estática: estos modelos existen en `app/backend/db/models.py` pero **no hay referencias** en `routes/` ni `classes/`.

## Antes de borrar en MySQL

1. Backup completo de la base `pie360`.
2. En producción: `SELECT COUNT(*) FROM <tabla>;` — si hay filas, investigar origen.
3. Confirmar que ningún reporte externo use esas tablas.

## Grupo ERP (heredado)

| Tabla probable | Modelo |
|----------------|--------|
| shoppings | ShoppingModel |
| shopping_products | ShoppingProductModel |
| sales | SaleModel |
| sale_products | SaleProductModel |
| products | ProductModel |
| categories | CategoryModel |
| inventories | InventoryModel |
| lots | LotModel |
| lot_items | LotItemModel |
| inventory_lot_items | InventoryLotItemModel |
| inventory_movements | InventoryMovementModel |
| inventory_audits | InventoryAuditModel |
| pre_inventory_stocks | PreInventoryStockModel |
| suppliers | SupplierModel |
| supplier_categories | SupplierCategoryModel |
| customer_product_discounts | CustomerProductDiscountModel |
| unit_measures | UnitMeasureModel |
| liter_features | LiterFeatureModel |
| unit_features | UnitFeatureModel |
| locations | LocationModel |

## IA / agente (ya eliminadas del código)

Si aún existieran en algún entorno:

```sql
DROP TABLE IF EXISTS evaluator_chat_psychoped_section_uses;
DROP TABLE IF EXISTS evaluator_chat_audits;
DROP TABLE IF EXISTS chat_details;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS ai_conversations;
DROP TABLE IF EXISTS knowledge_documents;
```

## Rutas huérfanas

- `routes/document_41_reports.py` existe pero **no está registrado** en `api/router.py`. Registrar o eliminar según negocio.
