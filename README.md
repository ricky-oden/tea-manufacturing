# TEA-V1 お茶製造管理システム

PLAN_VERSION: `TEA-V1.0`

製茶会社における原料入荷、製造指示、工程、設備、在庫、出荷、集計、マスタ、CSV取込を題材に、業務システムの処理を学ぶための単一事業所向けアプリケーションです。

現在は計画文書の作成段階です。アプリケーション、Docker Compose、migration、GitHub Actionsは未実装です。

## 採用技術

- frontend: Node.js 22、React、TypeScript、Vite、React Router、TanStack Query、React Hook Form、共通fetch client、Jest、React Testing Library
- backend: Python 3.12、FastAPI、SQLAlchemy、Alembic、pytest
- database: PostgreSQL 16
- environment: Docker Compose、npm

## 計画文書

- [実装計画](docs/implementation-plan.md)
- [要件と受入条件](docs/requirements.md)
- [進捗](docs/status.md)
- [意思決定記録](docs/decision-log.md)
- [システム概要](docs/system-overview.md)
- [画面一覧](docs/screen-list.md)
- [API仕様](docs/api-specification.md)
- [データモデル](docs/data-model.md)
- [製造状態](docs/manufacturing-status.md)
- [在庫トランザクション](docs/inventory-transaction.md)
- [CSV取込](docs/csv-import-specification.md)
- [テスト戦略](docs/test-strategy.md)

## 予定ポート

| service | host | container/network |
|---|---:|---:|
| frontend | 5174 | 5174 |
| backend | 8001 | 8001 |
| PostgreSQL | 未公開を基本とする | `db:5432` |

セットアップ手順と実行コマンドは、基盤実装後に実在するコマンドだけを追記します。
