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
PostgreSQL 16
```

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
