# TEA-V1 製造状態と操作制御

PLAN_VERSION: `TEA-V1.0`

対応要件: `TEA-FR-003`、`TEA-FR-004`、`TEA-FR-010`、`TEA-FR-012`、`TEA-NFR-003`

## 状態

| 表示名 | API/DB値 | 意味 |
|---|---|---|
| 下書き | `DRAFT` | 製造内容を編集中で、製造指示として未確定 |
| 指示済み | `ISSUED` | 製造内容を確定し、開始可能 |
| 製造中 | `IN_PROGRESS` | 原料を消費し、工程を実行中 |
| 完了 | `COMPLETED` | 製造を完了し、製品在庫へ反映済み |
| 取消 | `CANCELLED` | 製造しないことが確定した終了状態 |

## 許可遷移

```text
DRAFT ──issue──> ISSUED ──start──> IN_PROGRESS ──complete──> COMPLETED
  │                  │
  └────cancel────────┴──cancel──> CANCELLED
```

許可する遷移は次の5つだけとする。

1. 下書き→指示済み
2. 下書き→取消
3. 指示済み→製造中
4. 指示済み→取消
5. 製造中→完了

製造開始時に原料を減算するため、製造中→取消は通常操作として許可しない。製造開始後の誤りを訂正する業務手順は未確定であり、TEA-V1.0では通常状態遷移に含めない。

## 状態別操作

| 操作 | 下書き | 指示済み | 製造中 | 完了 | 取消 |
|---|---:|---:|---:|---:|---:|
| 詳細参照 | 可 | 可 | 可 | 可 | 可 |
| 製品・予定数量・予定日編集 | 可 | 不可 | 不可 | 不可 | 不可 |
| 原料・予定使用量編集 | 可 | 不可 | 不可 | 不可 | 不可 |
| 設備編集 | 可 | 不可 | 不可 | 不可 | 不可 |
| 指示確定 | 可 | 不可 | 不可 | 不可 | 不可 |
| 製造開始 | 不可 | 可 | 不可 | 不可 | 不可 |
| 工程実績入力 | 不可 | 不可 | 可 | 不可 | 不可 |
| 製造完了 | 不可 | 不可 | 可 | 不可 | 不可 |
| 取消 | 可 | 可 | 不可 | 不可 | 不可 |
| 物理削除 | 不可 | 不可 | 不可 | 不可 | 不可 |

## 遷移前条件

### 指示確定

- 製品、予定数量、予定日、原料、予定使用量、設備が有効である。
- 数量が正数である。
- 在庫はこの時点では減算しない。

### 製造開始

- 現在状態が`ISSUED`である。
- 必要な茶葉・品種マスタが有効である。
- 原料在庫が予定使用量以上ある。
- 製造指示、対象原料在庫行をlock取得後に再検証する。
- 原料減算、増減履歴、`IN_PROGRESS`への変更を同一transactionで行う。

### 製造完了

- 現在状態が`IN_PROGRESS`である。
- Phase 2では工程行0件を許容し、工程行がないことを完了拒否理由にしない。
- 製造指示と製品在庫行をlock取得後に再検証する。
- 製品加算、増減履歴、`COMPLETED`への変更を同一transactionで行う。

Phase 3で工程行が存在する場合に完了必須工程がすべて完了している条件を追加する。工程名、工程数、必須工程はPhase 3まで未確定とし、Phase 2でダミー工程を作成しない。歩留まり計算は行わないため、製造指示の予定数量を製品在庫へ加算する。

### 取消

- 現在状態が`DRAFT`または`ISSUED`である。
- 在庫更新は行わない。
- `CANCELLED`後は読み取り専用とする。

## 禁止操作の処理

- frontendは不可能な操作を非表示またはdisabledにし、その理由を表示する。
- backendは対象行を取得して現在状態を再確認する。
- 不正遷移、二重開始、二重完了は`409 Conflict`と統一エラー形式で返す。
- 競合で拒否した場合、状態、在庫残高、在庫履歴を変更しない。
- URL直打ちやrequest改変でも禁止操作を実行できないことをAPI testで確認する。

## 状態変更API

- `POST /api/v1/manufacturing-orders/{id}/issue`
- `POST /api/v1/manufacturing-orders/{id}/start`
- `POST /api/v1/manufacturing-orders/{id}/complete`
- `POST /api/v1/manufacturing-orders/{id}/cancel`

状態を直接指定する汎用更新APIは設けない。

## Phase 2検証根拠

- `DRAFT → CANCELLED`と`ISSUED → CANCELLED`をAPI testで確認する。
- `DRAFT`からstart／complete、`ISSUED`からcomplete、`IN_PROGRESS`からissue／cancel、`COMPLETED`と`CANCELLED`からの再操作をparameterized API testで拒否確認する。
- 各拒否で`409`、`INVALID_STATUS_TRANSITION`、状態・残高・履歴の無更新を確認する。
- frontend component testで`IN_PROGRESS`には製造完了だけを表示し、操作中disabledと操作失敗表示を確認する。
