# TEA-V1 お茶製造管理システム

PLAN_VERSION: `TEA-V1.0`

製茶会社における原料入荷、製造指示、工程、設備、在庫、出荷、集計、マスタ、CSV取込を題材に、業務システムの処理を学ぶための単一事業所向けアプリケーションです。

Phase 1の開発基盤として、health表示、統一APIエラー、Docker Compose、Alembic、テスト、手動実行限定CIを実装しています。製造、在庫、マスタ、CSV等の業務機能はまだ未実装です。

## 採用技術

- frontend: Node.js 22.23.2、React 19.2.8、TypeScript 5.9.3、Vite 8.2.1、React Router 7.18.2、TanStack Query 5.101.4、React Hook Form 7.85.0、Jest 29.7.0、React Testing Library 16.3.2
- backend: Python 3.12.13、FastAPI 0.141.1、SQLAlchemy 2.0.52、psycopg 3.3.4、Pydantic 2.13.4、Alembic 1.19.1、pytest 9.1.1、Ruff 0.16.2
- database: PostgreSQL 16.14
- environment: Docker Compose、npm

Base imageは`node:22.23.2-bookworm-slim`、`python:3.12.13-slim-trixie`、`postgres:16.14-trixie`へ固定しています。frontendはdevelopment containerとVite production build用のbuild stageまでを提供し、production配信runtimeやdeploymentはPhase 1の対象外です。backendはdevelopment targetとruntime targetを分離しています。

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

## ポートと接続

| service | host | container/network |
|---|---:|---:|
| frontend | 5174 | 5173 |
| backend | 8001 | 8000 |
| PostgreSQL | 非公開 | `db:5432` |
| test PostgreSQL | 非公開 | `test-db:5432` |

ブラウザは`http://localhost:5174/api/v1`へアクセスし、ViteがDocker network内の`http://backend:8000`へproxyします。backendは`db:5432`へ接続します。ブラウザからcontainer名へ直接接続しません。

## 環境変数

開発用の例をコピーします。

```bash
cp .env.example .env
```

`.env`はGit管理外です。`.env.example`の値はローカル学習専用であり、実環境の秘密値を記録しないでください。

## Docker Composeによるローカル起動

```bash
docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose ps
```

- frontend: `http://localhost:5174`
- backend health: `http://localhost:8001/api/v1/health`
- Vite proxy経由health: `http://localhost:5174/api/v1/health`

停止時は開発DBのnamed volumeを残します。

```bash
docker compose down
```

## Alembic

業務モデルとrevisionはPhase 2以降に追加します。Phase 1では起動と差分検査だけを提供します。

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic check
```

## frontend commands

```bash
docker compose exec frontend npm ci
docker compose run --rm --no-deps frontend npm run format
docker compose run --rm --no-deps frontend npm run format:check
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run build
```

依存は`frontend/package-lock.json`で固定します。
development containerの`node_modules`はnodeユーザー所有のnamed volumeとし、非rootで`npm ci`を再実行できます。

## backend commands

```bash
docker compose run --rm --no-deps backend ruff format .
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
```

### test-dbとpytest

`test-db`はtest profileだけで起動し、tmpfsを使用します。開発DBのnamed volumeとは共有しません。

```bash
docker compose --profile test up -d --wait test-db
docker compose run --rm --no-deps backend pytest
```

pytest開始時に、FastAPI applicationをimportする前に`TEST_DATABASE_URL`を検証し、検証済みURLを`DATABASE_URL`へ適用します。settings、engine、session factoryのcacheを初期化してからアプリを生成するため、`TestClient`からアプリ本体の`get_db`を利用した場合も`test-db:5432/tea_manufacturing_test`へ接続します。DB名が`_test`で終わらない、URLが不正、または環境変数がない場合は、engine生成と接続より前にpytestを停止します。test-db停止時は接続に失敗し、開発DBへfallbackしません。

test-dbに対するmigration確認:

```bash
docker compose run --rm --no-deps \
  -e DATABASE_URL=postgresql+psycopg://tea_test:tea_test_password@test-db:5432/tea_manufacturing_test \
  -e TEST_DATABASE_URL=postgresql+psycopg://tea_test:tea_test_password@test-db:5432/tea_manufacturing_test \
  backend python -m app.db.test_guard
docker compose run --rm --no-deps \
  -e DATABASE_URL=postgresql+psycopg://tea_test:tea_test_password@test-db:5432/tea_manufacturing_test \
  -e TEST_DATABASE_URL=postgresql+psycopg://tea_test:tea_test_password@test-db:5432/tea_manufacturing_test \
  backend alembic upgrade head
docker compose run --rm --no-deps \
  -e DATABASE_URL=postgresql+psycopg://tea_test:tea_test_password@test-db:5432/tea_manufacturing_test \
  -e TEST_DATABASE_URL=postgresql+psycopg://tea_test:tea_test_password@test-db:5432/tea_manufacturing_test \
  backend alembic check
```

test用migration guardは、`DATABASE_URL`と`TEST_DATABASE_URL`の双方が`_test`で終わり、同じ接続先である場合だけ成功します。

Python runtime依存は`backend/requirements.txt`、development/test依存は`backend/requirements-dev.txt`へ完全version固定しています。backend runtime imageにはpytest、Ruff、httpx2を含めません。

## GitHub Actions

`.github/workflows/ci.yml`は`workflow_dispatch`による手動実行だけを許可します。workflow権限は`contents: read`に限定し、push、pull request、schedule trigger、artifact保存、deployは設定していません。

## Phase 1の範囲

実装済み:

- `/api/v1/health`
- validation、404、conflict、unexpected errorの統一形式
- React/TanStack Queryによるhealth loading・success・error表示
- 共通fetch clientと共通APIエラー型
- PostgreSQL接続、Alembic、test DB guard
- formatter、lint、test、build、Docker Compose、手動CI基盤

未実装:

- 製造指示、工程、設備、在庫、入荷、出荷、集計
- 茶葉、品種、仕入先、設備、製品マスタ
- CSV取込

## Runtime version確認元

- [Node.js 22 release archive](https://nodejs.org/en/download/archive/v22)
- [Python official image tags](https://hub.docker.com/_/python/tags?name=3.12)
- [PostgreSQL official image tags](https://hub.docker.com/_/postgres/tags?name=16)
