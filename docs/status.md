# TEA-V1 状況

PLAN_VERSION: `TEA-V1.0`

更新日: 2026-08-12

## 現在フェーズ

Phase 0: 計画固定（完了）／Phase 1: 開発基盤（完了）／Phase 2: 最初の縦切り（完了）／Phase 3: 入荷・工程・設備（実装・検証完了、commit承認待ち）

TEA-V1.0は2026-08-10に初期正本として承認済み。Phase 1の開発基盤、Phase 2の最初の縦切り、Phase 3の原料入荷・固定工程・設備管理を実装・検証した。後続フェーズの在庫参照、出荷、集計、CSV等は未実装である。

## 要件状況

| 要件ID | 要件 | 計画済み | 実装済み | 検証済み |
|---|---|---|---|---|
| TEA-FR-001 | ダッシュボード | はい | いいえ | いいえ |
| TEA-FR-002 | 原料入荷 | はい | はい | はい |
| TEA-FR-003 | 製造指示 | はい | いいえ | いいえ |
| TEA-FR-004 | 工程管理 | はい | はい | はい |
| TEA-FR-005 | 設備管理 | はい | はい | はい |
| TEA-FR-006 | 在庫管理 | はい | いいえ | いいえ |
| TEA-FR-007 | 出荷 | はい | いいえ | いいえ |
| TEA-FR-008 | 集計 | はい | いいえ | いいえ |
| TEA-FR-009 | マスタ管理 | はい | いいえ | いいえ |
| TEA-FR-010 | 製造状態と操作制御 | はい | はい | はい |
| TEA-FR-011 | 製品マスタCSV取込 | はい | いいえ | いいえ |
| TEA-FR-012 | 製造指示から在庫更新までの結合処理 | はい | はい | はい |
| TEA-NFR-001 | API契約と統一エラー | はい | はい | はい |
| TEA-NFR-002 | ページング | はい | いいえ | いいえ |
| TEA-NFR-003 | 在庫取引の整合性と重複拒否 | はい | いいえ | いいえ |
| TEA-NFR-004 | 再現可能な開発環境 | はい | はい | はい |
| TEA-NFR-005 | 自動テスト | はい | いいえ | いいえ |
| TEA-NFR-006 | 手動起動限定CI | はい | はい | いいえ |
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

Phase 3の検証結果をユーザーが確認し、commitを承認すること。

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
