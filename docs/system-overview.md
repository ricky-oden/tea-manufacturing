# TEA-V1 システム概要

PLAN_VERSION: `TEA-V1.0`

対応要件: `TEA-FR-001`〜`TEA-FR-012`、`TEA-NFR-001`〜`TEA-NFR-007`

## 目的と利用範囲

TEA-V1は、製茶会社の原料入荷、製造、設備、在庫、出荷、集計を一元管理する学習用Webシステムである。単一事業所での利用を前提とし、認証、ログイン、ユーザー権限は扱わない。

## 全体構成

```text
Browser
  ↓
React / React Router
  ├─ React Hook Form: 入力状態と画面検証
  ├─ TanStack Query: server stateと再取得
  └─ 共通fetch client: HTTPと統一エラー変換
  ↓ /api/v1
FastAPI
  ├─ router: HTTP境界
  ├─ Pydantic schema: request/response検証
  ├─ service/use-case: 業務ルールとtransaction境界
  └─ SQLAlchemy: 永続化
  ↓
PostgreSQL 16.14
```

## Phase 1 開発基盤

- frontendはNode.js 22.23.2、backendはPython 3.12.13、DBはPostgreSQL 16.14に固定する。
- ブラウザは`localhost:5174`、backendは`localhost:8001`で公開する。PostgreSQL portは公開しない。
- Viteが`/api/v1`をDocker network内の`backend:8000`へproxyする。
- backendは同期SQLAlchemy Sessionとpsycopg 3で`db:5432`へ接続する。
- test profileの`test-db`は`tea_manufacturing_test`をtmpfsで保持し、開発DB volumeと分離する。
- pytestはapplication import前に検証済み`TEST_DATABASE_URL`を`DATABASE_URL`へ適用し、SQLAlchemy engineとsession factoryを遅延生成する。
- Phase 1で実装するAPIは`GET /api/v1/health`だけとし、業務API・Modelは作成しない。

## Phase 2 最初の縦切り

- 茶葉、品種、設備、製品の必要最小限のマスタと、製造指示・使用原料・在庫残高・増減履歴をPostgreSQLへ追加する。
- 製造指示の登録・一覧・詳細と、issue/start/complete/cancelを`/api/v1`配下へ追加する。
- 製造開始では原料残高と履歴、製造完了では製品残高と履歴を状態変更と同一transactionで更新する。
- 原料・製品数量は`kg`、`NUMERIC(15, 3)`、backend `Decimal`とする。
- 工程行は作らず、0件でも製造完了可能とする。工程条件はPhase 3で追加する。

## Phase 3 入荷・工程・設備

- 仕入先、原料入荷ヘッダー・明細、固定製造工程をPhase 2 schemaへ追加する。
- 原料入荷は即時確定し、複数明細、原料残高、`RECEIPT`履歴を1 transactionで保存する。
- 残高行は茶葉・品種の自然キー順に確保・lockし、同時入荷の加算を直列化する。
- issue時に蒸熱・揉捻・乾燥の3工程を一度だけ作成し、製造中にsequence順で開始・完了する。
- 工程行が存在する注文は全工程完了後だけ製造完了でき、Phase 2の工程0件注文には経過措置を維持する。
- 設備一覧・登録・編集・有効無効を提供し、無効設備の新規利用を拒否して過去参照を維持する。

## 主要業務フロー

### 原料入荷

```text
入荷登録
→ 入力・マスタ検証
→ 入荷記録
→ 原料在庫加算
→ 在庫増減履歴
→ commit
```

### 製造

```text
下書き
→ 指示済み
→ 製造開始
→ 原料在庫減算
→ 工程実績
→ 製造完了
→ 製品在庫加算
```

製造開始と製造完了は別々の短いtransactionとし、製造期間全体を1つのDB transactionにはしない。

### 出荷

```text
出荷登録
→ 出荷確定
→ 製品在庫検証
→ 製品在庫減算
→ 在庫増減履歴
→ commit
```

### CSV取込

```text
製品マスタCSV
→ ファイル・全行検証
├─ エラーあり: 登録0件、エラーCSV出力
└─ エラーなし: 全件を1 transactionで登録
```

## 責務分離

| 層 | 責務 | 担当しないこと |
|---|---|---|
| page/component | 表示、入力、操作受付 | 在庫整合性の最終保証 |
| query/form | server state、入力状態 | DB transaction |
| fetch client | HTTP、JSON、共通エラー変換 | 業務状態遷移 |
| router/schema | HTTP契約、型、形式検証 | 複数モデルの更新順序 |
| service/use-case | 状態遷移、在庫更新、CSV業務検証 | UI表示 |
| SQLAlchemy/PostgreSQL | 永続化、制約、lock、transaction | frontendの操作制御 |

## システム境界

- 外部API、外部ストレージ、決済、メール送信は持たない。
- ロット、賞味期限、複数倉庫、単位換算、歩留まりは扱わない。
- 設備は製造指示に関連付けるが、高度な予約競合管理は行わない。
