# TEA-V1 画面一覧

PLAN_VERSION: `TEA-V1.0`

認証・権限による画面分岐は設けない。URLはReact Routerで管理する。

| URL候補 | 画面 | 主な機能 | 要件ID |
|---|---|---|---|
| `/` | ダッシュボード | 状態別製造件数、在庫概況、期間集計 | TEA-FR-001 |
| `/raw-material-receipts` | 原料入荷一覧 | 検索、ページング、詳細遷移 | TEA-FR-002、TEA-NFR-002 |
| `/raw-material-receipts/new` | 原料入荷登録 | 入荷入力、確認、登録 | TEA-FR-002 |
| `/raw-material-receipts/:receiptId` | 原料入荷詳細 | 入荷内容、関連在庫履歴 | TEA-FR-002、TEA-FR-006 |
| `/manufacturing-orders` | 製造指示一覧 | 検索、状態表示、ページング | TEA-FR-003、TEA-FR-010 |
| `/manufacturing-orders/new` | 製造指示登録 | 下書き登録 | TEA-FR-003 |
| `/manufacturing-orders/:orderId` | 製造指示詳細 | 内容、状態操作、工程、在庫履歴 | TEA-FR-003、TEA-FR-004、TEA-FR-010、TEA-FR-012 |
| `/manufacturing-orders/:orderId/edit` | 製造指示編集 | 下書き編集 | TEA-FR-003、TEA-FR-010 |
| `/masters/equipment` | 設備管理 | 設備一覧、登録、詳細表示、編集、有効・無効 | TEA-FR-005、TEA-FR-009 |
| `/equipment` | 設備管理（Phase 3互換URL） | 設備一覧、登録、編集、有効・無効 | TEA-FR-005 |
| `/inventory/raw-materials` | 原料在庫 | 残高、ページング | TEA-FR-006 |
| `/inventory/products` | 製品在庫 | 残高、ページング | TEA-FR-006 |
| `/inventory/transactions` | 在庫増減履歴 | 対象・種別・期間検索 | TEA-FR-006 |
| `/shipments` | 出荷一覧 | 検索、ページング、詳細遷移 | TEA-FR-007 |
| `/shipments/new` | 出荷登録 | 複数明細の下書き登録 | TEA-FR-007 |
| `/shipments/:shipmentId` | 出荷詳細 | 下書き編集・確定、確定後読み取り専用 | TEA-FR-007 |
| `/reports` | 集計 | 期間指定、入荷・製造・出荷集計 | TEA-FR-008 |
| `/masters/tea-leaves` | 茶葉マスタ | 一覧、登録、詳細表示、編集、有効・無効、ページング | TEA-FR-009 |
| `/masters/varieties` | 品種マスタ | 一覧、登録、詳細表示、編集、有効・無効、ページング | TEA-FR-009 |
| `/masters/suppliers` | 仕入先マスタ | 一覧、登録、詳細表示、編集、有効・無効、ページング | TEA-FR-009 |
| `/masters/products` | 製品マスタ | 一覧、登録、詳細表示、編集、有効・無効、ページング | TEA-FR-009 |
| `/imports/products` | 製品CSV取込 | file選択、同期取込、Job結果・複数エラー表示、エラーCSV取得 | TEA-FR-011 |
| その他 | Not Found | 存在しない画面であることを表示 | TEA-NFR-001 |

## 共通表示要件

- 取得中、データなし、エラーを文字情報で示す。
- 登録・状態変更中は同じ操作を連続送信できない表示にする。
- frontendのdisabledは補助制御とし、backendでも必ず再検証する。
- API validation errorは入力欄付近、業務競合・通信失敗は共通alert領域に表示する。
- 一覧は`page`、`page_size`をURL queryと同期する。
- 在庫履歴の検索条件と集計期間もURL queryへ同期する。
- 在庫・出荷数量は`kg`を明示し、状態は色だけに依存せず文字で表示する。

## 状態別UI

製造指示詳細の状態別操作は`docs/manufacturing-status.md`を正とする。画面上の非表示・disabledだけで状態遷移の正当性を保証しない。
