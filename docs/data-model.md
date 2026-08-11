# TEA-V1 データモデル

PLAN_VERSION: `TEA-V1.0`

対応要件: `TEA-FR-002`〜`TEA-FR-012`、`TEA-NFR-003`

## 共通方針

- PostgreSQL 16系とSQLAlchemyを使用し、schema履歴はAlembicで管理する。
- 主キー、作成日時、更新日時を共通項目とする。
- マスタは一意な`code`、`name`、`is_active`を持ち、物理削除しない。
- 業務データは過去時点の参照を保つため、無効化済みマスタとの外部キーを保持する。
- 数量は`numeric`系で保持する。基準単位とscaleは詳細設計で確定する。
- ロット、賞味期限、倉庫、単位換算、歩留まりの列・tableは作らない。

## マスタ

| model候補 | 主な項目 | 主な制約 |
|---|---|---|
| `TeaLeaf` | code、name、is_active | code unique |
| `Variety` | code、name、is_active | code unique |
| `Supplier` | code、name、is_active | code unique |
| `Equipment` | code、name、is_active | code unique |
| `Product` | code、name、variety_id、is_active | code unique、variety FK |

品種と茶葉の関係は業務資料から確定できないため、両者を独立マスタとし、入荷・使用原料が両方を参照する初期設計とする。関係を必須化するかは詳細設計で決定する。

## 原料入荷

### `RawMaterialReceipt`

- receipt_number: 一意な入荷番号
- received_date
- supplier_id
- created_at

### `RawMaterialReceiptLine`

- receipt_id
- tea_leaf_id
- variety_id
- quantity

1つの入荷に複数明細を持てる構造とする。初期UIで1明細だけ扱う場合もDB構造はヘッダー・明細を分ける。

## 製造

### `ManufacturingOrder`

- order_number: 一意な製造指示番号
- product_id
- planned_quantity
- planned_date
- equipment_id
- status: `DRAFT`、`ISSUED`、`IN_PROGRESS`、`COMPLETED`、`CANCELLED`
- started_at
- completed_at
- created_at / updated_at

### `ManufacturingMaterial`

- manufacturing_order_id
- tea_leaf_id
- variety_id
- planned_quantity

### `ManufacturingProcess`

- manufacturing_order_id
- sequence
- process_name
- status
- started_at
- completed_at
- result_note

工程名、工程数、追加実績項目は詳細設計で決定する。製造状態とは別に工程単位の進捗を保持する。

## 在庫

### `RawMaterialInventoryBalance`

- tea_leaf_id
- variety_id
- quantity
- updated_at
- `(tea_leaf_id, variety_id)` unique

### `ProductInventoryBalance`

- product_id
- quantity
- updated_at
- `product_id` unique

### `InventoryTransaction`

- inventory_kind: `RAW_MATERIAL` / `PRODUCT`
- transaction_type: `RECEIPT` / `MANUFACTURING_CONSUMPTION` / `MANUFACTURING_OUTPUT` / `SHIPMENT`
- tea_leaf_id / variety_id / product_id: 種別に応じた参照
- quantity_delta: 加算は正、減算は負
- balance_after
- reference_type
- reference_id
- occurred_at

残高と履歴は同じservice transactionからだけ更新する。通常利用向けの残高直接更新APIは設けない。

## 出荷

### `Shipment`

- shipment_number: 一意な出荷番号
- shipped_date
- status: 確定前状態を採用する場合は`DRAFT` / `CONFIRMED`
- confirmed_at

### `ShipmentLine`

- shipment_id
- product_id
- quantity

出荷確定前状態を設けるかは未確定である。いずれの方式でも、同じ出荷を複数回在庫反映できないDB状態とservice検証を持つ。

## CSV取込

### `CsvImportJob`

- import_type: 初期値は`PRODUCT_MASTER`
- file_name
- status: `PROCESSING` / `SUCCEEDED` / `FAILED`
- total_rows
- success_rows
- error_rows
- created_at / completed_at

### `CsvImportError`

- csv_import_job_id
- row_number
- field_name
- error_code
- error_message
- input_value

エラーCSVをDB項目から再構成するか、生成物として一時保存するかは実装時に外部サービスを使わない方法で決定する。

## 主要な関係

```text
Supplier 1 --- * RawMaterialReceipt 1 --- * RawMaterialReceiptLine
TeaLeaf 1 --- * RawMaterialReceiptLine
Variety 1 --- * RawMaterialReceiptLine

Product 1 --- * ManufacturingOrder 1 --- * ManufacturingMaterial
Equipment 1 --- * ManufacturingOrder
ManufacturingOrder 1 --- * ManufacturingProcess

TeaLeaf/Variety 1 --- 1 RawMaterialInventoryBalance
Product 1 --- 1 ProductInventoryBalance

Shipment 1 --- * ShipmentLine * --- 1 Product
CsvImportJob 1 --- * CsvImportError
```

## DB制約候補

- マスタcode、各業務番号のunique制約
- quantityおよびplanned_quantityの正数check制約
- inventory balanceの0以上check制約
- 製造状態、取引種別のenumまたはcheck制約
- 工程sequenceの製造指示内unique制約
- 在庫残高の自然キーunique制約

業務状態遷移そのものはDB制約だけに依存せず、serviceで検証する。
