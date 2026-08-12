# TEA-V1 製品マスタCSV取込仕様

PLAN_VERSION: `TEA-V1.0`

対応要件: `TEA-FR-011`、`TEA-NFR-001`、`TEA-NFR-005`

## 対象

初期のCSV取込対象は製品マスタだけとする。他マスタ、原料入荷、製造指示、在庫、出荷は対象外とする。

## ファイル仕様

- 形式: header付きCSV
- multipart field名: `file`
- 拡張子: `.csv`
- 最大ファイルサイズ: 1 MiB
- 最大データ行数: 1,000行
- 文字コード: UTF-8。UTF-8 BOMの有無は受け入れる。
- 空行: ファイル末尾の空行は無視し、それ以外の空行は行エラーとする。
- header名と順序は次のとおりとする。

```csv
product_code,product_name,variety_code,is_active
P001,煎茶A,V001,true
```

| 項目 | 必須 | 内容 |
|---|---:|---|
| `product_code` | はい | 製品を一意に識別するコード |
| `product_name` | はい | 製品名 |
| `variety_code` | はい | 登録済みで有効な品種コード |
| `is_active` | はい | `true`または`false` |

`product_code`は30文字以下、`product_name`は100文字以下とし、画面登録・DB列と同じ制約を使用する。

## 正常系

1. uploadされたファイル名、形式、文字コード、headerを検証する。
2. 全行を構文解析する。
3. 全行の必須、型、文字長、値域を検証する。
4. CSV内の製品コード重複を検証する。
5. DB既存製品コードとの重複を検証する。
6. 品種コードの存在と有効性を検証する。
7. エラーが0件であることを確認する。
8. 1つのDB transactionで製品を全件登録する。
9. 成功状態、総行数、成功件数、エラー件数0を結果として保存する。

## 異常系

| 分類 | 例 | 結果 |
|---|---|---|
| file | CSVでない、読取不能、UTF-8でない | 製品登録0件、file error |
| header | 不足、余分、名称違い、順序違い | 製品登録0件、header error |
| empty | データ行0件 | 製品登録0件、empty file error |
| required | code、name、variety、activeの空値 | 製品登録0件、row error |
| format | `is_active`がtrue/false以外 | 製品登録0件、row error |
| length | codeまたはnameが上限超過 | 製品登録0件、row error |
| duplicate in file | 同じproduct_codeが複数行 | 製品登録0件、該当行error |
| duplicate in DB | 既存product_code | 製品登録0件、row error |
| reference | 品種なし、無効品種 | 製品登録0件、row error |
| database | 登録途中の制約違反・接続例外 | 全製品rollback、取込失敗 |

1件でもエラーがあれば、正常行を含めて製品を1件も登録しない。エラー情報と取込結果の記録は、製品一括登録とは分けて保存可能にする。

## エラーCSV

header:

```csv
row_number,field_name,error_code,error_message,input_value
```

| 項目 | 内容 |
|---|---|
| `row_number` | headerを1行目とした入力ファイル上の行番号。file/header errorは0 |
| `field_name` | 対象header名。ファイル全体の場合は空文字 |
| `error_code` | 機械判定可能な安定したコード |
| `error_message` | 利用者向け説明 |
| `input_value` | エラーとなった入力値 |

初期error code候補:

- `INVALID_FILE_TYPE`
- `INVALID_ENCODING`
- `INVALID_HEADER`
- `EMPTY_FILE`
- `REQUIRED`
- `INVALID_FORMAT`
- `MAX_LENGTH`
- `DUPLICATE_IN_FILE`
- `DUPLICATE_IN_DATABASE`
- `REFERENCE_NOT_FOUND`
- `REFERENCE_INACTIVE`
- `DATABASE_ERROR`

CSVとして正しくescapeし、カンマ、改行、引用符を含む入力値でも列が崩れないことをtestする。

## 取込結果

- job ID
- file name
- status: processing / succeeded / failed
- total rows
- success rows
- error rows
- accepted/completed timestamps
- error CSV取得可否

エラーがある場合の`success_rows`は0とする。全件正常時だけ入力データ行数と一致する。

## API

- `POST /api/v1/imports/products`
- `GET /api/v1/imports/products/{job_id}`
- `GET /api/v1/imports/products/{job_id}/errors.csv`

upload request内で同期処理する。外部queueや外部storageは使用しない。CSV解析とエラーCSV生成にはPython標準`csv`を使用する。ファイル未指定は統一`422`、1 MiB超過は統一`413`、CSV業務validation失敗は保存済みFAILED Jobとして返す。
