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

## PROPOSED_CHANGE履歴

なし。
