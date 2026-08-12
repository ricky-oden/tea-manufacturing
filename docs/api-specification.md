# TEA-V1 API仕様

PLAN_VERSION: `TEA-V1.0`

base path: `/api/v1`

## 共通仕様

### JSON

- request/responseはCSVファイル送受信を除きJSONとする。
- 日付は`YYYY-MM-DD`、日時はtimezoneを含むISO 8601文字列とする。
- 数量は浮動小数点誤差を避ける型としてbackend/DBで扱い、JSON上は数値として返す。
- 原料・製品数量の単位は`kg`、最小値は`0.001`、小数3桁とする。backendは`Decimal`、DBは`NUMERIC(15, 3)`を正とする。

### ページング

request query:

```text
page=1&page_size=20
```

response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0
}
```

`page_size`の既定値は20、上限は100とし、Phase 2以降のページングAPIで共通利用する。

### 統一エラー

```json
{
  "code": "INVALID_STATUS_TRANSITION",
  "message": "現在の製造状態では実行できません。",
  "field_errors": [
    {
      "field": "status",
      "code": "not_allowed",
      "message": "完了済みの製造指示は変更できません。"
    }
  ]
}
```

| HTTP status | 用途候補 |
|---:|---|
| 400 | query、ファイル、業務入力の不正 |
| 404 | 対象データなし |
| 409 | 状態競合、重複操作、在庫不足、コード重複 |
| 422 | FastAPI/Pydanticの形式検証エラーを統一形式へ変換 |
| 500 | 予期しないエラー。内部情報を応答へ露出しない |

項目に紐づかない場合も`field_errors`は空配列として返す。

## endpoint一覧

### Platform

| method | path | 用途 | 要件ID |
|---|---|---|---|
| GET | `/health` | backend health取得。`{"status":"ok"}`を返す | TEA-NFR-001、TEA-NFR-004 |

### Dashboard / reports

| method | path | 用途 | 要件ID |
|---|---|---|---|
| GET | `/dashboard?date_from=&date_to=` | 概況取得 | TEA-FR-001 |
| GET | `/reports/summary?date_from=&date_to=&group_by=` | 期間集計 | TEA-FR-008 |

### Raw material receipts

| method | path | 用途 | 要件ID |
|---|---|---|---|
| GET | `/raw-material-receipts` | 一覧 | TEA-FR-002 |
| POST | `/raw-material-receipts` | 入荷登録と原料在庫加算 | TEA-FR-002、TEA-NFR-003 |
| GET | `/raw-material-receipts/{receipt_id}` | 詳細 | TEA-FR-002 |

### Manufacturing orders / processes

| method | path | 用途 | 要件ID |
|---|---|---|---|
| GET | `/manufacturing-orders` | 一覧 | TEA-FR-003 |
| POST | `/manufacturing-orders` | 下書き登録 | TEA-FR-003 |
| GET | `/manufacturing-orders/{order_id}` | 詳細 | TEA-FR-003 |
| PUT | `/manufacturing-orders/{order_id}` | 下書き編集 | TEA-FR-003、TEA-FR-010 |
| POST | `/manufacturing-orders/{order_id}/issue` | 下書き→指示済み | TEA-FR-010 |
| POST | `/manufacturing-orders/{order_id}/start` | 製造開始・原料減算 | TEA-FR-010、TEA-FR-012 |
| POST | `/manufacturing-orders/{order_id}/complete` | 製造完了・製品加算 | TEA-FR-010、TEA-FR-012 |
| POST | `/manufacturing-orders/{order_id}/cancel` | 許可状態から取消 | TEA-FR-010 |
| GET | `/manufacturing-orders/{order_id}/processes` | 工程一覧・実績 | TEA-FR-004 |
| PUT | `/manufacturing-orders/{order_id}/processes/{process_id}` | 工程実績更新 | TEA-FR-004 |

状態操作を汎用`PUT`から分離し、serviceで遷移と在庫更新を一体として扱う。

Phase 3の工程更新requestは`action: start | complete`、任意の`equipment_id`、`result_note`を持つ。製造中以外、前工程未完了、重複操作、無効設備を統一エラーで拒否する。

### Inventory

| method | path | 用途 | 要件ID |
|---|---|---|---|
| GET | `/inventories/raw-materials` | 原料残高 | TEA-FR-006 |
| GET | `/inventories/products` | 製品残高 | TEA-FR-006 |
| GET | `/inventory-transactions` | 増減履歴 | TEA-FR-006 |

在庫残高の汎用POST/PUT/PATCH endpointは設けない。

### Shipments

| method | path | 用途 | 要件ID |
|---|---|---|---|
| GET | `/shipments` | 一覧 | TEA-FR-007 |
| POST | `/shipments` | 出荷登録 | TEA-FR-007 |
| GET | `/shipments/{shipment_id}` | 詳細 | TEA-FR-007 |
| PUT | `/shipments/{shipment_id}` | 未確定出荷の編集 | TEA-FR-007 |
| POST | `/shipments/{shipment_id}/confirm` | 出荷確定・製品減算 | TEA-FR-007、TEA-NFR-003 |

出荷の確定前状態を設けるかは未確定であり、設けない場合は登録と確定を1つのPOSTに統合する。

### Masters

resourceは`tea-leaves`、`varieties`、`suppliers`、`equipment`、`products`とする。

| method | path pattern | 用途 | 要件ID |
|---|---|---|---|
| GET | `/masters/{resource}` | 一覧 | TEA-FR-009 |
| POST | `/masters/{resource}` | 登録 | TEA-FR-009 |
| GET | `/masters/{resource}/{id}` | 詳細 | TEA-FR-009 |
| PUT | `/masters/{resource}/{id}` | 編集・有効無効変更 | TEA-FR-009 |

DELETE endpointは設けない。

Phase 2では最初の縦切りに必要な`tea-leaves`、`varieties`、`equipment`、`products`のGET一覧とPOST登録を実装する。詳細・編集・有効無効の管理画面は各マスタの担当フェーズで補完する。

Phase 3では`supplier`のGET一覧・POST登録を追加し、`equipment`のGET詳細・PUT編集／有効無効変更を追加する。原料入荷POSTは即時在庫反映し、複数明細を受け付ける。

### Product CSV imports

| method | path | 用途 | 要件ID |
|---|---|---|---|
| POST | `/imports/products` | CSV検証・一括取込 | TEA-FR-011 |
| GET | `/imports/products/{job_id}` | 結果取得 | TEA-FR-011 |
| GET | `/imports/products/{job_id}/errors.csv` | エラーCSV取得 | TEA-FR-011 |

## 共通fetch client

- API base URLを一箇所で設定する。
- JSON request/responseと非2xx応答を共通処理する。
- 統一エラーをTypeScriptの共通エラー型へ変換する。
- 業務固有メッセージやTanStack Queryのcache keyはfeature側で管理する。
- 認証header処理は実装しない。
