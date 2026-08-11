# Repository Instructions

PLAN_VERSION: `TEA-V1.0`

## Authoritative documents

- `docs/implementation-plan.md`
- `docs/requirements.md`
- `docs/status.md`
- `docs/decision-log.md`

## Plan Alignment Gate

実装、監査、設計変更の前に次を行う。

1. 本ファイルを読む。
2. `docs/implementation-plan.md`、`docs/requirements.md`を全文読む。
3. `docs/status.md`、`docs/decision-log.md`を読む。
4. `PLAN_VERSION`、現在フェーズ、対象要件IDを報告する。
5. 許可された変更と禁止された変更を報告する。
6. 依頼と承認済み計画に差異があれば実装せず、差異を報告する。

## Change governance

`CAREER-SYSTEMS-V1`または`TEA-V1.0`の確定事項を変更する必要がある場合だけ、`PROPOSED_CHANGE`として差分、理由、影響、代替案を提示し、明示承認を待つ。承認前の通常の詳細設計案には`PROPOSED_CHANGE`を使用しない。

承認後の計画変更は`docs/decision-log.md`に記録し、必要な場合だけ`PLAN_VERSION`を更新する。進捗だけを理由に計画を全面的に書き換えない。

## Scope and safety

- 採用技術、業務範囲、要件を独断で追加、削除、変更しない。
- 認証、ログイン、ユーザー権限を追加しない。
- 対象外機能を実装しない。
- 外部サービスへ接続せず、本番デプロイを追加しない。
- GitHub Actionsの初期トリガーは`workflow_dispatch`だけとする。
- push、PR作成、デプロイは明示指示がある場合だけ行う。
- ユーザーの変更と無関係な作業ツリー変更を保持する。
- 実装、テスト、文書、要件IDの対応を維持する。
- 未実行または失敗中の検証を「検証済み」と記録しない。

## Status vocabulary

- 計画済み: 承認対象の要件と受入条件が文書化されている。
- 実装済み: 要件を満たすコードと必要なテストが存在する。
- 検証済み: 承認済みの検証を実行し、成功結果を記録している。

3状態は別々に管理する。計画済みであっても、実装済みまたは検証済みとは限らない。
