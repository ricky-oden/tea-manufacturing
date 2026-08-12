# TEA-V1 意思決定記録

PLAN_VERSION: `TEA-V1.0`

この文書にはユーザーが確定した決定と、承認済みの計画変更だけを記録する。

## 2026-08-10: TEA-V1.0初期計画

状態: 承認済み

承認日: 2026-08-10

### 技術

- Node.js 22系、Python 3.12系、PostgreSQL 16系
- React、TypeScript、Vite、React Router
- `@tanstack/react-query`、React Hook Form、共通fetch client
- FastAPI、SQLAlchemy、Alembic
- Jest、React Testing Library、pytest
- Docker Compose、npm
- Python依存はruntime用とdevelopment/test用に分離する。

### 業務・データ

- 学習用の単一事業所システムとする。
- 認証、ログイン、ユーザー権限は対象外とする。
- 製造状態は、下書き、指示済み、製造中、完了、取消とする。
- 原料は製造開始時に減算する。
- 製品在庫は製造完了時に加算する。
- 出荷確定時に製品在庫を減算する。
- 在庫残高と増減履歴を同一transactionで更新する。
- 二重開始、二重完了、二重出荷をbackendで拒否する。
- CSV取込は最初は製品マスタを対象とする。
- CSVに1件でもエラーがあればファイル全体を登録しない。
- エラーCSVは行番号、項目、コード、メッセージ、入力値を含む。
- マスタ削除は行わず、有効・無効で管理する。

### API・運用

- APIは`/api/v1`配下とする。
- 一覧は`page`と`page_size`でページングする。
- APIエラーはトップレベルに`code`、`message`、`field_errors`を持つ。
- GitHub Actionsの初期トリガーは`workflow_dispatch`だけとする。
- pushは明示指示がある場合だけ行う。

### 対象外

- ロット追跡、賞味期限、複数倉庫・保管場所、単位換算、歩留まり計算
- 設備予約の高度な競合管理、Playwright、外部サービス、本番デプロイ

## 2026-08-12: Phase 1開発基盤の詳細設計

状態: 承認済み

### Runtimeとpackage

- Node.js 22.23.2、Python 3.12.13、PostgreSQL 16.14へpatch versionを固定する。
- Docker imageは`node:22.23.2-bookworm-slim`、`python:3.12.13-slim-trixie`、`postgres:16.14-trixie`を使用する。
- frontend package名は`tea-manufacturing-frontend`、backend application packageは`app`、backendプロジェクト表記は`tea-manufacturing-backend`とする。
- frontend依存は`package-lock.json`、Python依存はruntime/development-testに分けて完全version固定する。
- backend runtime targetにpytest、Ruff等のdevelopment依存を含めない。

### DatabaseとDocker

- 開発DBは`tea_manufacturing`、ユーザーは`tea_app`とする。
- test-dbは`tea_manufacturing_test`、ユーザーは`tea_test`とし、test profileのtmpfsで開発DB volumeから分離する。
- test DB名が`_test`で終わらない場合、接続前に失敗させる。
- PostgreSQL portはホストへ公開しない。
- frontendはホスト5174/container 5173、backendはホスト8001/container 8000とする。
- development containerはsource mountを使用し、frontendの`node_modules`はnamed volumeでホストから分離する。

### Backendとfrontend

- SQLAlchemy 2の同期Session、psycopg 3、Pydantic 2、pydantic-settings、Alembicを使用する。
- Phase 1のAPIは`GET /api/v1/health`だけとし、業務API・Modelは作成しない。
- validation、404、conflict、unexpected errorをトップレベル`code`、`message`、`field_errors`へ統一する。
- Viteはブラウザの`/api/v1`をDocker network内の`backend:8000`へproxyする。
- frontendのhealth状態はTanStack Queryで管理する。

### CI

- `.github/workflows/ci.yml`のtriggerは`workflow_dispatch`だけとする。
- jobは`frontend-test`、`frontend-build`、`backend-test`とする。
- GitHub Actions自体はPhase 1作業では実行せず、構造を静的確認する。

### Phase 1 commit前監査

- SQLAlchemy engineとsession factoryは遅延生成し、pytestはFastAPI application import前に検証済み`TEST_DATABASE_URL`を`DATABASE_URL`へ適用する。
- test用migrationは`DATABASE_URL`と`TEST_DATABASE_URL`が同一の`_test` DBを指すことを事前guardで確認する。
- Starlette TestClientはdevelopment/test依存の`httpx2 2.7.0`を使用する。
- GitHub Actionsのworkflow権限は`contents: read`へ限定する。
- frontendはdevelopment containerとVite production build用build stageまでとし、production配信runtimeとdeploymentは実装しない。
- frontendのnode_modules named volumeはnodeユーザー所有とし、development container内で非rootの`npm ci`を可能にする。

## PROPOSED_CHANGE履歴

なし。
