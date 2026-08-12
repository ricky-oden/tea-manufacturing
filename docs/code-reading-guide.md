# TEA-V1 コードリーディングガイド

PLAN_VERSION: `TEA-V1.0`

この文書は、要件から画面、HTTP境界、データモデル、業務処理、テストへ順にたどるための案内である。パス、class、functionはPhase 6時点の実在名を記載する。

## 最初に読む順序

1. `frontend/src/App.tsx`の`App`と`Layout`でURLと画面を確認する。
2. `frontend/src/api/client.ts`の`apiFetch`で共通HTTP・エラー変換を確認する。
3. `backend/app/main.py`の`create_app`と`backend/app/api/router.py`でAPI全体を確認する。
4. `backend/app/api/routes/`でrequestを受け、`backend/app/schemas/`で型と値域を確認する。
5. `backend/app/services/`で状態制御、transaction、lock、rollbackを追う。
6. `backend/app/models/manufacturing.py`と`backend/alembic/versions/`でDB制約とschema履歴を確認する。
7. `frontend/src/*.test.tsx`と`backend/tests/`で受入条件の証拠を確認する。

## 主要な処理導線

### 製造開始・完了

`OrderDetailPage` → `transitionOrder` → `manufacturing_orders.start/complete` → `manufacturing.start_order/complete_order` → `ManufacturingOrder`・在庫残高・`InventoryTransaction` → `test_manufacturing_orders.py`

`start_order`と`complete_order`は製造指示行と在庫行をlockし、状態を再検証してから残高と履歴を同じtransactionで更新する。強制例外、二重処理、PostgreSQL同時要求のテストを先に読むと境界が分かりやすい。

### 原料入荷・出荷

- 入荷: `ReceiptFormPage` → `createReceipt` → `phase3.add_receipt` → `phase3.create_receipt`
- 出荷: `ShipmentDetailPage` → `confirmShipment` → `phase4.confirm` → `phase4.confirm_shipment`

両処理とも複数在庫行を決定順でlockし、業務行・残高・履歴を同じtransactionへ含める。

### 製品CSV取込

`CsvImportPage` → `uploadProductCsv` → `csv_imports.upload_products_csv` → `csv_imports.import_products` → `CsvImportJob`・`CsvImportError`・`Product`・`ProductInventoryBalance`

検証失敗のJob保存と、DB登録途中例外後の安全な別transactionを区別して読む。

### 共通ページングとマスタ

`MasterManagementPage` → `fetchMasterPage` → `masters.masters` → `manufacturing.list_masters`。`backend/app/api/pagination.py`の`PAGE_SIZE_MAX`と`page_response`を、製造指示、入荷、在庫、出荷、全マスタが共有する。

## 要件トレーサビリティ

| 要件ID | 画面／component | API route | Model | service／共通処理 | 主なtest |
|---|---|---|---|---|---|
| TEA-FR-001 | `DashboardPanel` | `phase4.dashboard` | `ManufacturingOrder`、在庫残高 | `phase4.get_dashboard` | `Phase4.test.tsx`、`test_phase4.py` |
| TEA-FR-002 | `ReceiptListPage`、`ReceiptFormPage`、`ReceiptDetailPage` | `phase3.receipts/add_receipt/receipt_detail` | `RawMaterialReceipt`、`RawMaterialReceiptLine` | `phase3.create_receipt/list_receipts/get_receipt` | `Phase3.test.tsx`、`test_phase3.py` |
| TEA-FR-003 | `OrderListPage`、`OrderFormPage`、`OrderDetailPage` | `manufacturing_orders.orders/add_order/edit_order/order_detail` | `ManufacturingOrder`、`ManufacturingMaterial` | `manufacturing.create_order/update_order/list_orders/order_response` | `Manufacturing.test.tsx`、`Phase6.test.tsx`、`test_manufacturing_orders.py`、`test_phase6.py` |
| TEA-FR-004 | `ProcessPanel` | `phase3.processes/change_process` | `ManufacturingProcess` | `phase3.list_processes/update_process` | `Phase3.test.tsx`、`test_phase3.py` |
| TEA-FR-005 | `MasterManagementPage(resource="equipment")` | `masters.masters/add_master/master_detail/edit_master` | `Equipment` | `manufacturing.create_master/update_master/list_masters` | `Phase3.test.tsx`、`Phase6.test.tsx`、`test_phase3.py`、`test_phase6.py` |
| TEA-FR-006 | `InventoryBalancePage`、`InventoryTransactionsPage` | `phase4.raw_balances/product_balances/inventory_transactions` | 在庫残高、`InventoryTransaction` | `phase4.list_raw_balances/list_product_balances/list_inventory_transactions` | `Phase4.test.tsx`、`test_phase4.py` |
| TEA-FR-007 | `ShipmentListPage`、`ShipmentFormPage`、`ShipmentDetailPage` | `phase4.shipments/add_shipment/edit_shipment/confirm` | `Shipment`、`ShipmentLine` | `phase4.create_shipment/update_shipment/confirm_shipment` | `Phase4.test.tsx`、`test_phase4.py` |
| TEA-FR-008 | `ReportsPage` | `phase4.summary` | 入荷・製造・出荷・在庫 | `phase4.get_summary` | `Phase4.test.tsx`、`test_phase4.py` |
| TEA-FR-009 | `MasterManagementPage` | `masters` routerの4 endpoint | `TeaLeaf`、`Variety`、`Supplier`、`Equipment`、`Product` | `manufacturing.create_master/get_master/update_master/list_masters` | `Phase6.test.tsx`、`test_phase6.py` |
| TEA-FR-010 | `OrderDetailPage`、`actions` | issue/start/complete/cancel | `ManufacturingOrder.status` | `change_simple_status`、`issue_order`、`start_order`、`complete_order` | `Manufacturing.test.tsx`、`test_manufacturing_orders.py` |
| TEA-FR-011 | `CsvImportPage` | `csv_imports.import_products/import_job/import_errors` | `CsvImportJob`、`CsvImportError` | `csv_imports.import_products_csv/build_error_csv` | `CsvImportPage.test.tsx`、`test_csv_imports.py` |
| TEA-FR-012 | `OrderDetailPage` | start/complete | 製造指示、在庫残高、履歴 | `manufacturing.start_order/complete_order` | `test_manufacturing_orders.py` |
| TEA-NFR-001 | 全画面、`apiFetch` | `/api/v1`全route | `ApiError`相当schema | `core.errors.install_exception_handlers` | `client.test.ts`、`test_errors.py` |
| TEA-NFR-002 | 各一覧 | 製造指示、入荷、在庫、出荷、マスタ一覧 | 各一覧対象Model | `api.pagination.PAGE_SIZE_MAX/page_response` | `test_manufacturing_orders.py`、`test_phase4.py`、`test_phase6.py` |
| TEA-NFR-003 | 状態操作・出荷確定UI | start/complete/confirm | 在庫残高・履歴 | `start_order/complete_order/confirm_shipment` | `test_manufacturing_orders.py`、`test_phase4.py` |
| TEA-NFR-004 | `HealthPage` | health | SQLAlchemy Base | settings、session、test guard、Compose | `App.test.tsx`、`test_database.py`、`test_health.py` |
| TEA-NFR-005 | 全component | 全API | PostgreSQL schema | Jest/RTL、pytest fixture | frontend全test、backend全test |
| TEA-NFR-006 | なし | なし | PostgreSQL service container | `.github/workflows/ci.yml` | Phase 6静的検査（workflow本体は未実行） |
| TEA-NFR-007 | なし | なし | なし | `requirements.md`、`status.md`、本表 | 要件件数・実在パス・検証結果の文書監査 |

## migrationとdemo seed

- migration: `backend/alembic/versions/20260812_01_phase2_manufacturing.py`から`20260812_04_phase5_csv_imports.py`まで連続する。
- demo seed: `backend/app/db/seed.py`の`seed_demo_data`。PostgreSQLのupsertを使い、固定codeのマスタと製品在庫残高を冪等に作る。
- テスト保護: `backend/tests/conftest.py`がapplication import前にtest DBへ切り替え、`backend/app/db/test_guard.py`が`_test`接尾辞を検証する。

## 学習用と本番で追加が必要なもの

TEA-V1はローカルの単一事業所学習用である。本番では認証・認可、監査証跡、秘密情報管理、TLS、監視、バックアップ／復旧、可用性、性能・負荷試験、production frontend配信runtime、脆弱性対応、デプロイとロールバックが必要になる。これらは対象外であり、現在のコードに仮実装を置いていない。
