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

## 2026-08-12: Phase 2数量・完了条件の詳細設計

状態: 承認済み

- 原料・製品数量の基準単位は`kg`、最小値は`0.001 kg`、小数3桁とする。
- DBは`NUMERIC(15, 3)`、backendはPython `Decimal`を使用し、0以下を拒否する。
- frontendは`kg`を表示し、数量入力の`step`と`min`を`0.001`とする。
- 単位換算と別単位は追加しない。
- Phase 2では工程行を作成せず、工程行0件は製造完了の拒否理由としない。
- Phase 3で工程行が存在する場合の必須工程完了条件を追加する。工程名・工程数・必須工程は未確定のまま維持する。

## 2026-08-12: Phase 3入荷・工程・設備の詳細設計

状態: 承認済み

- 原料入荷は登録時に即時確定し、複数明細、残高、明細単位の`RECEIPT`履歴を同一transactionで保存する。DRAFTや承認待ちは設けない。
- 入荷番号は一意とし、再登録を`409 Conflict`で拒否する。仕入先、茶葉、品種は有効なマスタだけ新規利用できる。
- 数量はPhase 2と同じ`kg`、`NUMERIC(15, 3)`、Python `Decimal`とする。
- 固定工程は`STEAMING`（蒸熱）、`ROLLING`（揉捻）、`DRYING`（乾燥）の3工程、sequence 1〜3とし、全工程を必須とする。
- 工程状態は`PENDING`、`IN_PROGRESS`、`COMPLETED`とする。製造指示のissue時に3行を一度だけ作成する。
- 工程は製造指示が`IN_PROGRESS`の間だけ順序どおり操作でき、工程行が存在する指示は全工程完了後だけ製造完了できる。
- Phase 2で作成済みの工程0件注文は、工程完了gateを適用せず従来どおり完了可能とする。
- 設備は一覧、登録、編集、有効・無効切替を提供する。物理削除せず、無効設備の新規利用を拒否し、過去参照は維持する。
- 工程テンプレートの管理画面や自由編集、高度な設備予約競合管理は実装しない。

## 2026-08-12: Phase 4在庫・出荷・集計の詳細設計

状態: 承認済み

- 出荷は登録時`DRAFT`、確定時`CONFIRMED`とし、下書きだけ編集・確定できる。取消・物理削除は追加しない。
- 1出荷は1件以上の製品明細を持ち、同一出荷内の製品重複を禁止する。数量は`kg`、`NUMERIC(15, 3)`、Python `Decimal`、最小`0.001 kg`とする。
- 出荷確定では出荷行、product ID順の製品在庫行をlockし、状態・全在庫を再検証してから、残高減算、明細単位`SHIPMENT`履歴、確定状態・日時を同一transactionで保存する。
- 在庫不足、途中例外、二重・同時確定では部分更新を残さない。在庫残高を直接変更する汎用APIは設けない。
- 原料・製品残高はページングし、履歴は在庫種別、取引種別、茶葉、品種、製品、期間で検索する。
- 集計期間は開始日・終了日を必須とし、両端を含み、`Asia/Tokyo`で解釈する。入荷は`received_date`、製造完了は`completed_at`、確定出荷は`shipped_date`を基準とする。
- 集計は入荷・製造完了・確定出荷、現在庫、茶葉・品種別入荷、製品別製造・出荷を返し、未確定出荷を除外する。
- ダッシュボードは製造状態別件数、原料・製品在庫概況、指定期間の入荷・製造完了・確定出荷を返す。frontend初期期間は当日を含む直近30日とする。

## 2026-08-12: Phase 5製品マスタCSV取込の詳細設計

状態: 承認済み

- 製品マスタCSVだけをupload request内で同期処理し、Celery、Redis、外部queue、外部storageを使用しない。
- multipart fieldは`file`、拡張子は`.csv`、文字コードはUTF-8またはUTF-8 BOM付き、最大ファイルサイズは1 MiB、最大データ行数は1,000行とする。
- Python標準`csv`で解析し、末尾空行は無視、データ途中の空行は行エラーとする。`is_active`は小文字`true`または`false`だけを受け付ける。
- validation失敗は製品登録transactionを開始せず、FAILED Jobと可能な全行エラーを保存する。全行正常時は製品、`0.000 kg`の製品在庫残高、Job成功状態を同一transactionで保存する。
- DB途中例外は製品・残高をrollbackし、新しい安全なtransactionでFAILED Jobと`DATABASE_ERROR`を保存する。内部例外文字列は応答や保存エラーへ露出しない。
- エラーCSVはDBのJob別エラーから標準`csv`で同期生成し、外部storageや生成ファイルを永続化しない。
- FastAPIのmultipart解析に必要なruntime依存として`python-multipart==0.0.32`を完全固定する。

## 2026-08-12: Phase 6品質・学習用整備

状態: 承認済み

- 新しい業務領域を追加せず、正式19要件を実コードとテストへ対応付ける。
- 製造指示一覧の定義済み絞り込みは状態、製品、予定日の開始・終了とする。下書きだけを編集でき、詳細に原料、設備、工程、関連在庫履歴を含める。
- 茶葉、品種、仕入先、設備、製品は共通の一覧・登録・詳細・編集・有効無効を持ち、DELETE endpointを設けない。
- ページング対象APIは共通の既定20、上限100と、`items`、`page`、`page_size`、`total`、`total_pages`を使用する。
- 固定codeの学習用demo masterと製品在庫残高を、開発DBへ冪等に投入するローカル手順を提供する。
- Pydantic warningは一律非表示にせず、任意型へ付けたquery alias metadataをなくし、全pytestを`-W error`で検証する。
- GitHub Actionsは静的整合性だけを確認し、workflow本体は追加承認なしに実行しない。

## PROPOSED_CHANGE履歴

なし。
