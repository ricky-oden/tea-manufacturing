import { fireEvent, screen, waitFor } from "@testing-library/react";

import { uploadProductsCsv, type CsvImportJob } from "./api/csvImports";
import { renderApp } from "./test/renderApp";

jest.mock("./api/csvImports", () => ({
  ...jest.requireActual("./api/csvImports"),
  uploadProductsCsv: jest.fn(),
}));

const successJob: CsvImportJob = {
  id: 1,
  import_type: "PRODUCT_MASTER",
  file_name: "products.csv",
  status: "SUCCEEDED",
  total_rows: 2,
  success_rows: 2,
  error_rows: 0,
  accepted_at: "2026-08-12T00:00:00Z",
  completed_at: "2026-08-12T00:00:01Z",
  errors: [],
  error_csv_available: false,
};

const failedJob: CsvImportJob = {
  ...successJob,
  id: 2,
  status: "FAILED",
  success_rows: 0,
  error_rows: 2,
  error_csv_available: true,
  errors: [
    {
      row_number: 2,
      field_name: "product_code",
      error_code: "REQUIRED",
      error_message: "必須項目です。",
      input_value: "",
    },
    {
      row_number: 3,
      field_name: "variety_code",
      error_code: "REFERENCE_NOT_FOUND",
      error_message: "品種コードが見つかりません。",
      input_value: "V999",
    },
  ],
};

beforeEach(() => jest.resetAllMocks());

function selectFile(name = "products.csv") {
  const file = new File(
    ["product_code,product_name,variety_code,is_active\n"],
    name,
    {
      type: "text/csv",
    },
  );
  fireEvent.change(screen.getByLabelText("CSVファイル"), {
    target: { files: [file] },
  });
  return file;
}

test("初期表示にheaderと上限を示し未選択時はuploadできない", () => {
  renderApp("/imports/products");
  expect(
    screen.getByRole("heading", { name: "製品マスタCSV取込" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "ヘッダー: product_code,product_name,variety_code,is_active",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText(/最大1 MiB、最大1,000データ行/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "アップロード" })).toBeDisabled();
});

test("upload中はボタンをdisabledにして処理中表示する", async () => {
  jest
    .mocked(uploadProductsCsv)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/imports/products");
  const file = selectFile();
  fireEvent.click(screen.getByRole("button", { name: "アップロード" }));
  await waitFor(() => expect(uploadProductsCsv).toHaveBeenCalledTimes(1));
  expect(jest.mocked(uploadProductsCsv).mock.calls[0][0]).toBe(file);
  expect(screen.getByRole("button", { name: "取込処理中" })).toBeDisabled();
});

test("成功jobのstatusと件数を表示する", async () => {
  jest.mocked(uploadProductsCsv).mockResolvedValue(successJob);
  renderApp("/imports/products");
  selectFile();
  fireEvent.click(screen.getByRole("button", { name: "アップロード" }));
  expect(await screen.findByText("状態: SUCCEEDED")).toBeInTheDocument();
  expect(screen.getByText("成功件数: 2")).toBeInTheDocument();
  expect(screen.getByText("失敗件数: 0")).toBeInTheDocument();
});

test("失敗jobの複数エラーとerror CSV導線を表示する", async () => {
  jest.mocked(uploadProductsCsv).mockResolvedValue(failedJob);
  renderApp("/imports/products");
  selectFile();
  fireEvent.click(screen.getByRole("button", { name: "アップロード" }));
  expect(await screen.findByText("状態: FAILED")).toBeInTheDocument();
  expect(
    screen.getByText(/行2 \/ product_code \/ REQUIRED/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/行3 \/ variety_code \/ REFERENCE_NOT_FOUND/),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "エラーCSVをダウンロード" }),
  ).toHaveAttribute("href", "/api/v1/imports/products/2/errors.csv");
});

test("API失敗を表示する", async () => {
  jest.mocked(uploadProductsCsv).mockRejectedValue(new Error("network failed"));
  renderApp("/imports/products");
  selectFile();
  fireEvent.click(screen.getByRole("button", { name: "アップロード" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "CSV取込APIの呼び出しに失敗しました",
  );
});

test("同名ファイルを再選択・再送信でき既存job結果を保持する", async () => {
  jest
    .mocked(uploadProductsCsv)
    .mockResolvedValueOnce(failedJob)
    .mockRejectedValueOnce(new Error("retry failed"));
  renderApp("/imports/products");
  selectFile();
  fireEvent.click(screen.getByRole("button", { name: "アップロード" }));
  expect(await screen.findByText("状態: FAILED")).toBeInTheDocument();

  const secondFile = selectFile();
  fireEvent.click(screen.getByRole("button", { name: "アップロード" }));
  await waitFor(() => expect(uploadProductsCsv).toHaveBeenCalledTimes(2));
  expect(jest.mocked(uploadProductsCsv).mock.calls[1][0]).toBe(secondFile);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.getByText("状態: FAILED")).toBeInTheDocument();
  expect(uploadProductsCsv).toHaveBeenCalledTimes(2);
});
