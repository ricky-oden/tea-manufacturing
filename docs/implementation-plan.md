# TEA-V1 実装計画

PLAN_VERSION: `TEA-V1.0`

上位計画: `CAREER-SYSTEMS-V1`

状態: 2026-08-10承認済みの初期正本。Phase 1開発基盤、Phase 2最初の縦切り、Phase 3入荷・工程・設備は実装・検証済み。

## 1. 目的

紙やExcelで管理されていた製茶会社の情報を題材に、ブラウザからREST API、業務ロジック、ORM、PostgreSQLまでの処理と、製造状態・在庫整合性・CSV検証を学べるシステムを構築する。

暗記ではなく、製造指示から在庫更新までの一往復、frontend/backend/databaseの責務、正常系と重要な異常系をコードとテストから説明できる状態を目指す。

## 2. システム境界

- 学習用の単一事業所システムとする。
- 対象業務は、ダッシュボード、原料入荷、製造指示、工程、設備、在庫、出荷、集計、マスタ、CSV取込とする。
- 認証、ログイン、ユーザー権限は対象外とする。
- 外部サービスと本番デプロイは対象外とする。
- 詳細な対象外一覧は「10. 対象外」を参照する。

## 3. 技術構成

| 区分 | 採用技術 |
|---|---|
| frontend runtime | Node.js 22.23.2 |
| frontend | React、TypeScript、Vite、React Router |
| server state | `@tanstack/react-query` |
| forms | React Hook Form |
| HTTP | 共通fetch client |
| frontend test | Jest、React Testing Library |
| backend runtime | Python 3.12.13 |
| backend | FastAPI、SQLAlchemy、Alembic |
| backend test | pytest |
| database | PostgreSQL 16.14 |
| local environment | Docker Compose |
| package manager | npm |
| Python dependencies | runtime用とdevelopment/test用を分離 |

各バージョンは該当するmajor/minor系列内でscaffold時に具体的なpatch versionを固定し、lockfileを管理する。系列変更は計画変更として扱う。

## 4. 要件範囲

正式な要件、受入条件、対応文書は`docs/requirements.md`を正とする。

- `TEA-FR-001` ダッシュボード
- `TEA-FR-002` 原料入荷
- `TEA-FR-003` 製造指示
- `TEA-FR-004` 工程管理
- `TEA-FR-005` 設備管理
- `TEA-FR-006` 在庫管理
- `TEA-FR-007` 出荷
- `TEA-FR-008` 集計
- `TEA-FR-009` マスタ管理
- `TEA-FR-010` 製造状態と操作制御
- `TEA-FR-011` CSV取込
- `TEA-FR-012` 製造指示から在庫更新までの結合処理
- `TEA-NFR-001` API契約と統一エラー
- `TEA-NFR-002` ページング
- `TEA-NFR-003` 在庫取引の整合性と重複拒否
- `TEA-NFR-004` 再現可能な開発環境
- `TEA-NFR-005` 自動テスト
- `TEA-NFR-006` 手動起動限定CI
- `TEA-NFR-007` 要件・実装・検証の追跡

## 5. アーキテクチャ方針

### frontend

- React RouterがURLと画面を対応付ける。
- TanStack QueryがAPI由来のserver state、取得中、失敗、再取得、更新後の無効化を管理する。
- React Hook Formが入力状態と画面側の入力検証を管理する。
- 共通fetch clientがbase URL、JSON変換、統一エラー変換を担当する。
- 業務単位を`features`として分け、共通UIとAPI契約を分離する。

### backend

- FastAPI routerがHTTP path、query、status codeを担当する。
- Pydantic schemaがrequest/responseの型と入力検証を担当する。
- service/use-case層が状態遷移、在庫更新、CSV取込等の業務ルールとtransaction境界を担当する。
- SQLAlchemy model/repositoryが永続化を担当する。
- AlembicがDB schema変更履歴を管理する。

### database

- PostgreSQLの外部キー、一意制約、check制約をアプリケーション検証と併用する。
- 在庫残高と増減履歴は同一transactionで更新する。
- 製造開始、製造完了、出荷確定では対象行をロックし、状態と在庫をtransaction内で再検証する。

### Docker Compose

- Compose project名は`tea-manufacturing`とする。
- `frontend`、`backend`、`db`の3サービスを基本とする。
- frontendはホスト`5174`からcontainer`5173`、backendはホスト`8001`からcontainer`8000`へ接続する。
- backendはCompose network内の`db:5432`へ接続する。
- 実`.env`は管理せず、開発用例だけを`.env.example`へ置く。

## 6. 最初の縦切り導線

```text
製造指示一覧
→ GET /api/v1/manufacturing-orders
→ FastAPI router / schema
→ service / SQLAlchemy
→ PostgreSQL
→ 状態表示
→ 許可された状態変更
→ 製造開始時の原料在庫減算
→ 製造完了時の製品在庫加算
```

CSV取込は、基盤とこの縦切り導線の完成後に独立した機能単位として実装する。

## 7. 実装フェーズ

### Phase 0: 計画固定

- 本計画と受入条件の承認
- 未確定事項の解消または実装を妨げない保留条件の明記
- 完了条件: `TEA-V1.0`の承認

### Phase 1: 開発基盤

- frontend/backendのscaffold
- PostgreSQL、Docker Compose、環境変数例
- healthcheck、共通fetch client、統一APIエラー
- formatter、lint、test、build、migration checkの再現可能なコマンド
- `workflow_dispatch`だけのGitHub Actions

### Phase 2: 最初の縦切り

- 必要最小限の茶葉、品種、設備、製品マスタ
- 製造指示一覧・登録・詳細
- 製造状態遷移と禁止操作
- 製造開始時の原料減算
- 製造完了時の製品加算
- DBを含む結合テスト

### Phase 3: 入荷・工程・設備

- 原料入荷と原料在庫加算
- 工程進捗・実績
- 設備一覧と有効・無効管理

### Phase 4: 在庫・出荷・集計

- 原料・製品の残高と増減履歴
- 出荷確定と製品在庫減算
- ダッシュボードと期間集計

### Phase 5: 製品マスタCSV取込

- CSV検証
- ファイル単位の全件登録または全件ロールバック
- エラーCSV出力

### Phase 6: 品質と学習用整備

- 要件単位のテスト補強
- Docker Compose上の結合確認
- 文書と実装の対応確認
- コードリーディング用の案内整備

## 8. 完了判定

要件ごとに次を独立して記録する。

1. 計画済み: 要件IDと受入条件が承認済み文書にある。
2. 実装済み: コードと必要なテストが存在する。
3. 検証済み: 承認済みの検証を実行し、成功結果を記録している。

すべての必須要件が実装済み・検証済みとなり、未実行または失敗中の必須検証がない場合だけTEA-V1を完成とする。

## 9. 変更管理

`CAREER-SYSTEMS-V1`または本計画の確定事項を変更する場合だけ`PROPOSED_CHANGE`を提示する。差分、理由、影響、代替案を説明し、承認後に`docs/decision-log.md`と必要な文書を更新する。

## 10. 対象外

- ロット追跡
- 賞味期限
- 複数倉庫・保管場所
- 単位換算
- 歩留まり計算
- 設備予約の高度な競合管理
- 認証、ログイン、ユーザー権限
- Playwright
- 外部サービス
- 本番デプロイ

## 11. 未確定事項

- ダッシュボードおよび集計の既定期間と表示指標の詳細
- 原料数量・製品数量の固定基準単位と小数桁数
- 製造開始後に誤りを発見した場合の業務上の訂正手順
- 出荷登録の確定前状態を設けるか

これらは確定事項を変更しない範囲で詳細設計時に決定する。上位計画または確定事項の変更が必要になった場合は`PROPOSED_CHANGE`とする。
