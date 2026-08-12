# TEA-V1 テスト戦略

PLAN_VERSION: `TEA-V1.0`

対応要件: `TEA-NFR-005`および各機能要件の受入条件

## 原則

- frontendはJestとReact Testing Library、backendはpytestを使用する。
- 重要な業務ルールは画面だけでなくservice/API/DB層で検証する。
- frontendのAPIはmockし、backendの在庫・transaction・集計はPostgreSQLを使用する。
- fixtureごとにデータを作成し、テスト順序に依存させない。
- 実行していない検証を検証済みと記録しない。
- Playwrightは使用しない。

## frontend test

### component/form

- 必須、型、正数、日付期間の入力エラー
- 共通入力、共通alert、pagination
- loading、データなし、APIエラー
- 送信中の連続操作抑止
- API失敗時の入力保持

### state control

- 製造状態ごとの表示、編集可否、操作ボタン
- 完了・取消の読み取り専用表示
- 不正操作に対するAPI `409`の表示

### TanStack Query / fetch client

- query成功・失敗
- mutation成功後の対象query無効化・再取得
- 統一APIエラーからfrontend共通型への変換
- pagination queryとURLの同期

frontend testはbackendのtransaction整合性を保証するものではない。

## backend unit/service test

- Pydantic schemaの必須・型・値域
- 許可された製造状態遷移
- すべての禁止遷移
- 無効マスタの新規利用拒否
- 工程順序と状態制御
- 統一エラーのcode、message、field_errors
- CSV parserと各validation rule

## backend API/DB integration test

- 原料入荷、残高加算、履歴作成
- 製造開始、複数原料減算、履歴、状態変更
- 原料不足時の全rollback
- 製造完了、製品加算、履歴、状態変更
- 出荷確定、製品減算、履歴、状態変更
- 製品不足時の全rollback
- 処理途中の強制例外による全rollback
- 二重開始、二重完了、二重出荷の拒否
- 同時要求時の行lockと再検証
- 残高が負数にならないDB制約
- 集計APIと元データの一致
- `page`、`page_size`と総件数
- code unique制約と有効・無効

## CSV test

- 正常なUTF-8、UTF-8 BOM付きファイル
- header不正、空ファイル、空行
- 必須、形式、文字長
- CSV内重複、DB重複
- 品種なし、無効品種
- 複数エラーの収集
- 1件エラー時に製品登録0件
- DB例外時の全rollback
- 正常時の全件登録
- エラーCSVの5列、行番号、escape
- 結果件数とstatus

## 結合シナリオ

### 最重要シナリオ

1. 必要マスタと原料入荷を登録する。
2. 製造指示を下書き登録する。
3. 指示済みに変更し、在庫が変化しないことを確認する。
4. 製造開始し、原料残高と履歴を確認する。
5. 工程実績を登録する。
6. 製造完了し、製品残高と履歴を確認する。
7. 再完了が拒否され、製品残高が変化しないことを確認する。
8. 出荷を確定し、製品残高と履歴を確認する。
9. 再出荷が拒否され、製品残高が変化しないことを確認する。

### CSVシナリオ

1. 有効な品種を登録する。
2. 正常CSVですべての製品が登録されることを確認する。
3. エラーを含むCSVで登録0件となることを確認する。
4. エラーCSVの内容が入力行と一致することを確認する。

## 要件トレーサビリティ

| 要件群 | frontend | backend unit/API | PostgreSQL integration |
|---|---:|---:|---:|
| TEA-FR-001、008 | 必須 | 必須 | 必須 |
| TEA-FR-002、003、004、005、009 | 必須 | 必須 | 必須 |
| TEA-FR-006、007、010、012 | 必須 | 必須 | 必須 |
| TEA-FR-011 | 必須 | 必須 | 必須 |
| TEA-NFR-001、002 | 必須 | 必須 | 必要箇所 |
| TEA-NFR-003 | 補助 | 必須 | 必須 |
| TEA-NFR-004 | 対象外 | smoke/check | 必須 |
| TEA-NFR-006 | 対象外 | workflow構文・手動実行 | PostgreSQL service利用 |
| TEA-NFR-007 | 文書監査 | 文書監査 | 検証結果記録 |

## 実行環境

- localとCIで同じnpm/pytestコマンドを利用できるようにする。
- CIは`workflow_dispatch`だけで起動する。
- formatter、lint、test、build、migration checkの具体的コマンドはscaffold後にREADMEへ記載する。
- Docker Compose上のfrontend→backend→PostgreSQL疎通を手動総合確認する。

## Phase 1 test

Phase 1では次だけを実装・検証対象とする。

- frontend App、health loading・success・error
- 共通fetch clientの正常responseと統一APIエラー変換
- backend health、validation、404、conflict、unexpected error
- unexpected error responseへ内部例外文字列を露出しないこと
- `TEST_DATABASE_URL`のDB名が`_test`で終わることを強制するguard
- pytest開始時、FastAPI application import前に検証済み`TEST_DATABASE_URL`を`DATABASE_URL`へ適用するbootstrap
- アプリ本体のengine、session、`get_db`がtmpfsのtest-dbを参照するDB接続smoke test
- test用migrationで`DATABASE_URL`と`TEST_DATABASE_URL`が同じ`_test` DBを指すことの事前guard
- 不正URL、危険なDB名、test-db停止時に開発DBへfallbackしない異常系
- Alembic upgradeとautogenerate差分check
- Docker Composeのdb/backend/frontend healthとVite proxy疎通

Phase 1のtest成功を、未実装の製造、在庫、出荷、マスタ、CSV要件の検証済み根拠にはしない。

## 現在の状態

Phase 1の基盤test、Docker Compose、手動CI定義を実装した。Starlette TestClientはdevelopment/test依存のhttpx2を使用する。業務機能testは該当フェーズまで未実装・未検証である。
