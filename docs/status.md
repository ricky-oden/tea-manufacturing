# TEA-V1 状況

PLAN_VERSION: `TEA-V1.0`

更新日: 2026-08-12

## 現在フェーズ

Phase 0: 計画固定（完了）／Phase 1: 開発基盤（完了）／Phase 2: 最初の縦切り（開始承認待ち）

TEA-V1.0は2026-08-10に初期正本として承認済み。Phase 1ではhealth、統一APIエラー、Docker Compose、Alembic、test、手動CIの開発基盤を実装した。製造、在庫、マスタ、CSV等の業務機能は未実装である。

## 要件状況

| 要件ID | 要件 | 計画済み | 実装済み | 検証済み |
|---|---|---|---|---|
| TEA-FR-001 | ダッシュボード | はい | いいえ | いいえ |
| TEA-FR-002 | 原料入荷 | はい | いいえ | いいえ |
| TEA-FR-003 | 製造指示 | はい | いいえ | いいえ |
| TEA-FR-004 | 工程管理 | はい | いいえ | いいえ |
| TEA-FR-005 | 設備管理 | はい | いいえ | いいえ |
| TEA-FR-006 | 在庫管理 | はい | いいえ | いいえ |
| TEA-FR-007 | 出荷 | はい | いいえ | いいえ |
| TEA-FR-008 | 集計 | はい | いいえ | いいえ |
| TEA-FR-009 | マスタ管理 | はい | いいえ | いいえ |
| TEA-FR-010 | 製造状態と操作制御 | はい | いいえ | いいえ |
| TEA-FR-011 | 製品マスタCSV取込 | はい | いいえ | いいえ |
| TEA-FR-012 | 製造指示から在庫更新までの結合処理 | はい | いいえ | いいえ |
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

ユーザーがPhase 2「最初の縦切り」の実装開始を明示承認すること。
