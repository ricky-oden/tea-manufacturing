# TEA-V1 データモデル

PLAN_VERSION: `TEA-V1.0`

対応要件: `TEA-FR-002`〜`TEA-FR-012`、`TEA-NFR-003`

## 共通方針

- PostgreSQL 16系とSQLAlchemyを使用し、schema履歴はAlembicで管理する。
- 主キー、作成日時、更新日時を共通項目とする。
- マスタは一意な`code`、`name`、`is_active`を持ち、物理削除しない。
- 業務データは過去時点の参照を保つため、無効化済みマスタとの外部キーを保持する。
- 原料・製品数量は`kg`を基準単位とし、`NUMERIC(15, 3)`で保持する。正の入力は最小`0.001 kg`、残高は0以上とする。
- backendは`Decimal`を使用し、JavaScriptの浮動小数点計算だけを正としない。
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
- process_code: `STEAMING` / `ROLLING` / `DRYING`
- process_name
- status: `PENDING` / `IN_PROGRESS` / `COMPLETED`
- equipment_id: 任意
- started_at
- completed_at
- result_note

製造指示内でsequenceとprocess_codeをそれぞれuniqueとする。製造状態とは別に工程単位の進捗を保持する。

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
- status: `DRAFT` / `CONFIRMED`
- confirmed_at
- created_at / updated_at

### `ShipmentLine`

- shipment_id
- product_id
- quantity

出荷は1件以上の明細を持ち、同一出荷内の同じ製品をunique制約で拒否する。数量は`NUMERIC(15, 3)`の正数とする。出荷番号は一意で、確定済み出荷はserviceで編集・再確定を拒否する。無効製品は新規明細へ利用できないが、既存明細の外部キー参照は保持する。

## CSV取込

### `CsvImportJob`

- import_type: 初期値は`PRODUCT_MASTER`
- file_name
- status: `PROCESSING` / `SUCCEEDED` / `FAILED`
- total_rows
- success_rows
- error_rows
- accepted_at / completed_at

### `CsvImportError`

- csv_import_job_id
- row_number
- field_name
- error_code
- error_message
- input_value

Jobは処理開始時に`PROCESSING`で保存し、検証または登録完了時に`SUCCEEDED`／`FAILED`へ更新する。`status`と`accepted_at`へindexを持つ。エラーはJob外部キーとJob ID indexを持ち、Job削除時はcascadeする。エラーCSVはJob別エラーからPython標準`csv`で同期生成し、ファイルを永続化しない。

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

## Phase 2 migration範囲

茶葉、品種、設備、製品、製造指示、使用原料、原料在庫残高、製品在庫残高、在庫増減履歴を作成する。仕入先、入荷、工程、出荷、CSV取込のtableは担当フェーズまで作成しない。

## Phase 3 migration範囲

Phase 2 revisionへ連続する1 revisionで、仕入先、原料入荷ヘッダー・明細、固定製造工程を追加し、在庫取引種別へ`RECEIPT`を追加する。入荷数量の正数check、入荷番号unique、工程sequence/process codeの製造指示内unique、外部キーをDB制約として持つ。

## Phase 4 migration範囲

Phase 3 revisionへ連続する1 revisionで、出荷ヘッダー・明細を追加し、在庫取引種別へ`SHIPMENT`を追加する。出荷番号unique、同一出荷内製品unique、数量正数check、製品外部キーをDB制約として持つ。集計とダッシュボードは既存業務tableから算出し、集計専用tableは追加しない。

## Phase 5 migration範囲

Phase 4 revisionへ連続する1 revisionで`csv_import_jobs`、`csv_import_errors`、取込種別・状態enum、Job外部キー、status・受付日時・Job ID indexを追加する。製品と製品在庫残高は既存tableへ同一transactionで登録する。
