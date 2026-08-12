# TEA-V1 状況

PLAN_VERSION: `TEA-V1.0`

更新日: 2026-08-12

## 現在フェーズ

Phase 0からPhase 5: 完了／Phase 6: 品質と学習用整備（実装・検証完了、未commit）

TEA-V1.0は2026-08-10に初期正本として承認済み。Phase 1からPhase 5は確定済みであり、Phase 6で正式19要件の実装・検証対応を補完した。Phase 6差分は未stage・未commitである。

## 要件状況

| 要件ID | 要件 | 計画済み | 実装済み | 検証済み |
|---|---|---|---|---|
| TEA-FR-001 | ダッシュボード | はい | はい | はい |
| TEA-FR-002 | 原料入荷 | はい | はい | はい |
| TEA-FR-003 | 製造指示 | はい | はい | はい |
| TEA-FR-004 | 工程管理 | はい | はい | はい |
| TEA-FR-005 | 設備管理 | はい | はい | はい |
| TEA-FR-006 | 在庫管理 | はい | はい | はい |
| TEA-FR-007 | 出荷 | はい | はい | はい |
| TEA-FR-008 | 集計 | はい | はい | はい |
| TEA-FR-009 | マスタ管理 | はい | はい | はい |
| TEA-FR-010 | 製造状態と操作制御 | はい | はい | はい |
| TEA-FR-011 | 製品マスタCSV取込 | はい | はい | はい |
| TEA-FR-012 | 製造指示から在庫更新までの結合処理 | はい | はい | はい |
| TEA-NFR-001 | API契約と統一エラー | はい | はい | はい |
| TEA-NFR-002 | ページング | はい | はい | はい |
| TEA-NFR-003 | 在庫取引の整合性と重複拒否 | はい | はい | はい |
| TEA-NFR-004 | 再現可能な開発環境 | はい | はい | はい |
| TEA-NFR-005 | 自動テスト | はい | はい | はい |
| TEA-NFR-006 | 手動起動限定CI | はい | はい | はい（静的検証） |
| TEA-NFR-007 | 要件・実装・検証の追跡 | はい | はい | はい |

「計画済み」は承認済みの本計画文書に要件と受入条件が記載されたことを示す。実装済み・検証済みとは別に管理する。

## Phase 1範囲の状態

| 要件ID | Phase 1実装 | Phase 1検証 | 備考 |
|---|---|---|---|
| TEA-NFR-001 | 完了 | 完了 | health、validation、404、conflict、500、共通fetch client |
| TEA-NFR-004 | 完了 | 完了 | 固定runtime、Compose、DB分離、README command |
| TEA-NFR-005 | 完了 | 完了 | Phase 1基盤testのみ。業務testを含む要件全体は未完了 |
| TEA-NFR-006 | 完了 | 静的検証完了 | GitHub Actions自体は指示どおり未実行 |
| TEA-NFR-007 | 完了 | 完了 | 要件・実装・検証状態を本書で分離管理 |

## 検証状況

- 文書間整合性検査: 2026-08-10実施、正式要件19件と進捗表19件が一致
- 指定14ファイルの存在確認: 2026-08-10実施、欠落なし
- Markdown末尾空白検査: 2026-08-10実施、問題なし
- `git diff --check`: 2026-08-12実施、問題なし
- frontend: Prettier check、ESLint、Jest 6件、Vite production build成功。production配信runtimeとdeploymentは未実装
- frontend再現性: Node.js 22.23.2上で`npm ci`成功、`package-lock.json`のSHA-256が実行前後で一致、node_modules named volumeを非root更新可能
- backend: Ruff format check、Ruff lint、pytest 13件成功、pytest warningなし
- migration: 開発DBとtest-dbで`alembic upgrade head`、`alembic check`成功
- Docker Compose: config、build、up、全healthcheck成功
- 疎通: backend health、frontend起動、Vite proxy health、backend→開発DB接続成功
- DB分離: 開発DBはnamed volume、test-dbはtmpfs、双方ともhost port非公開を確認
- container user: backendはUID 10001、frontendはUID 1000で非root実行を確認
- backend runtime target: pytest、Ruffを含まないことを確認
- test DB安全性: pytest開始時に検証済み`TEST_DATABASE_URL`をアプリの`DATABASE_URL`へ適用し、TestClientの`get_db`が`test-db:5432/tea_manufacturing_test`へ接続することを確認
- test DB異常系: 不正URLと`_test`でないDB名を接続前に拒否し、test-db停止時に開発DBへfallbackしないことを確認
- warning監査: Starlette TestClientを公式案内のhttpx2へ移行しdeprecation warningを解消。npm推移依存のdeprecated warningとDocker build stageのroot pip warningは残存
- GitHub Actions: `workflow_dispatch`限定、`contents: read`、3 job、concurrency、timeoutを静的確認。workflow自体は未実行

## 次の承認ゲート

Phase 6の実装・検証結果をユーザーが確認し、commitを承認すること。GitHub Actions workflow本体は未実行であり、実行には別途明示承認を要する。

## Phase 2範囲の状態

- 数量仕様: `kg`、`NUMERIC(15, 3)`、backend `Decimal`、frontend `step=0.001`
- Model/migration: 茶葉、品種、設備、製品、製造指示・使用原料、原料・製品残高、在庫履歴
- API: 必要マスタの一覧・登録、製造指示の登録・一覧・詳細、issue/start/complete/cancel
- frontend: 製造指示一覧・登録・詳細、loading/error/empty、状態別操作
- 工程: Phase 2では行を作成せず、0件でも製造完了可能。Phase 3の具体定義は未確定
- Phase 2検証: Jest 15件、pytest 30件、frontend/backend formatter・lint、Vite build、Compose config/up、開発DBのAlembic checkが成功
- `TEA-FR-010`: `DRAFT`・`ISSUED`からの取消、代表的な禁止遷移7件、状態・残高・履歴の無更新、frontend状態別操作を直接検証
- `TEA-FR-012`: PostgreSQL transaction内のflush後強制例外で状態・原料残高・製品残高・履歴の全rollbackと統一500を直接検証
- 同時開始: 独立session／connectionの2要求で1成功・1拒否、原料残高`7.000 kg`、消費履歴1件、製造状態`IN_PROGRESS`を確認
- ページング: 5件に対するpage 1/2、page size 2、total 5、total pages 3、重複なし、状態絞り込み、不正値の統一validation errorを確認
- 接続DB: 開発`db:5432/tea_manufacturing`、test`test-db:5432/tea_manufacturing_test`。数量列`NUMERIC(15, 3)`を実DBで確認
- `TEA-FR-003/005/006/009`はPhase 2該当部分を実装したが、編集、工程、管理画面等の後続受入条件が残るため要件全体は未実装・未検証のままとする。
- `TEA-NFR-002/003/005`も後続API・出荷・業務testが残るため要件全体は未完了とする。

## Phase 3範囲の状態

- Model/migration: 仕入先、原料入荷・明細、固定製造工程、`RECEIPT`取引種別をPhase 2に連続するrevisionで追加
- 入荷: 即時確定、複数明細、決定順lock、残高・履歴同一transaction、重複番号・無効マスタ・数量制御
- 工程: issue時に蒸熱・揉捻・乾燥を1回だけ作成し、製造中だけsequence順に開始・完了。全工程完了gateと工程0件経過措置を実装
- 設備: 一覧、登録、詳細、編集、有効無効。無効設備の新規利用を拒否し、過去参照を維持
- frontend: 入荷一覧・複数明細登録、工程panel、設備管理。loading/error/empty/disabled/入力保持/cache再取得を実装
- Phase 3検証: Jest 25件、pytest 38件、frontend/backend lint・format、Vite build、Compose config/build/up、開発/test DB migration・Alembic check、backend/Vite proxy APIが成功
- 接続DB: 開発`db:5432/tea_manufacturing`（named volume保持）、test`test-db:5432/tea_manufacturing_test`（tmpfs、clean migration検証）
- `TEA-FR-002/004/005`は受入条件を実装・検証済み。`TEA-FR-009`は茶葉・品種・仕入先・製品の編集等が後続のため要件全体は未完了とする。

## Phase 4範囲の状態

- Model/migration: `DRAFT`・`CONFIRMED`を持つ出荷ヘッダー、複数製品明細、`SHIPMENT`取引種別をPhase 3に連続するrevisionで追加
- 在庫参照: 原料・製品残高のページング一覧と、在庫種別・取引種別・各マスタ・期間による履歴検索を実装。残高の汎用更新APIは設けない
- 出荷: 下書き登録・一覧・詳細・編集、複数明細の確定、製品残高減算、明細単位履歴を同一transactionで実装。確定後は読み取り専用
- transaction: 出荷行とproduct ID順の製品残高行をlock後に再検証し、在庫不足・途中例外では全rollback、同時確定では1件だけ成功することをPostgreSQLで確認
- 集計: `Asia/Tokyo`で両端を含む必須期間を検証し、入荷・製造完了・確定出荷、現在庫、マスタ別内訳を集計。未確定出荷を除外
- dashboard: 製造状態別件数、原料・製品在庫概況、指定期間の3数量を表示し、frontend初期期間を当日を含む直近30日とする
- frontend: 在庫3画面、出荷3画面、集計画面、ダッシュボードを追加し、loading/error/empty、URL query、pagination、validation、disabled、入力保持、読み取り専用、cache更新を実装
- Phase 4検証: Jest 43件、pytest 46件、frontend/backend lint・format、Vite build、開発/test DB migration・Alembic check、ComposeとAPI疎通を実施
- 接続DB: 開発`db:5432/tea_manufacturing`（named volume保持）、test`test-db:5432/tea_manufacturing_test`（tmpfs、clean migration検証）
- `TEA-FR-001/006/007/008`と`TEA-NFR-003`は受入条件を実装・検証済み。`TEA-NFR-002/005`は後続のマスタ・CSV等を含む全体完了まで未完了とする。

## Phase 5範囲の状態

- Model/migration: `CsvImportJob`、`CsvImportError`、取込種別・状態enum、外部キー・indexをPhase 4から連続するrevisionで追加
- 処理: 製品マスタCSVをrequest内で同期処理。UTF-8/BOM、`.csv`、1 MiB、1,000行、header、必須・長さ・真偽値、各重複、品種存在・有効性を決定順で検証
- transaction: validation失敗は製品登録を開始せずFAILED Jobと全エラーを保存。正常時はProduct、`0.000 kg`のProductInventoryBalance、Job成功状態を同一transactionで保存
- rollback: DB途中例外ではProduct・残高を全rollback後、別transactionでFAILED Jobと安全な`DATABASE_ERROR`を保存し、内部例外文字列を露出しない
- API/frontend: upload、Job詳細、Job別エラーCSVと`/imports/products`画面を実装。処理中disabled、結果保持、複数エラー、再選択、download導線を提供
- Phase 5検証: Jest 49件、pytest 71件、frontend/backend lint・format、Vite build、開発/test DB migration・Alembic check、backend/Vite proxy upload・error CSVが成功
- 接続DB: 開発`db:5432/tea_manufacturing`（named volume保持）、test`test-db:5432/tea_manufacturing_test`（tmpfs、clean migration検証）
- `TEA-FR-011`は実装・検証済み。`TEA-FR-009`は製品CSV登録部分のみ実装済みで、全マスタ管理要件は未完了のままとする。

## Phase 6範囲の状態

- 製造指示: 下書き編集、状態・製品・予定日期間の絞り込み、原料名・設備・工程・関連在庫履歴を含む詳細を補完した。
- マスタ: 茶葉、品種、仕入先、設備、製品を共通のページング一覧・登録・詳細表示・編集・有効無効へ統一し、DELETE endpointを設けない。無効マスタの新規利用拒否と過去参照維持を検証した。
- 共通ページング: 製造指示、入荷、原料・製品在庫、在庫履歴、出荷、全5マスタで既定20、上限100と共通応答を使用する。
- warning: Pydantic `UnsupportedFieldAttributeWarning`の原因だった任意型query alias metadataを除去し、pytest 78件を`-W error`で成功した。
- frontend: Jest 55件、ESLint、Prettier check、Vite production buildが成功した。
- backend: pytest 78件、Ruff lint・format checkが成功した。skip、xfail、pytest warningは0件。
- migration: 開発DBとclean test DBで`20260812_01`から`20260812_04`までupgrade・checkが成功し、test DBで`04→03→04`のdowngrade・再upgrade・checkも成功した。
- seed: 開発DBで2回実行し、固定codeの茶葉・品種・仕入先・設備・製品・製品残高が各1件であることを確認した。pytestでも冪等性を検証した。
- Docker/API: Compose config・build・up・health、backend直接とVite proxy経由のhealth・マスタページングAPIが成功した。
- CI: `workflow_dispatch`だけ、`contents: read`、concurrency、`cancel-in-progress: true`、全job timeoutを静的確認した。workflow本体は未実行。
- 文書: `docs/code-reading-guide.md`へ実在パス・class・functionと要件→画面→API→Model→service→test対応表を追加した。
- 正式19要件はすべて計画済み・実装済み・検証済みである。TEA-V1.0対象外と本番運用に必要な追加事項は実装していない。
