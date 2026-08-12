import { fireEvent, screen, waitFor } from "@testing-library/react";

import { fetchMasters } from "./api/manufacturing";
import {
  confirmShipment,
  createShipment,
  fetchDashboard,
  fetchInventoryTransactions,
  fetchProductBalances,
  fetchRawBalances,
  fetchShipment,
  fetchShipments,
  fetchSummary,
} from "./api/phase4";
import { renderApp } from "./test/renderApp";

jest.mock("./api/manufacturing", () => ({
  fetchMasters: jest.fn(),
}));
jest.mock("./api/phase4", () => ({
  ...jest.requireActual("./api/phase4"),
  fetchRawBalances: jest.fn(),
  fetchProductBalances: jest.fn(),
  fetchInventoryTransactions: jest.fn(),
  fetchShipments: jest.fn(),
  fetchShipment: jest.fn(),
  createShipment: jest.fn(),
  updateShipment: jest.fn(),
  confirmShipment: jest.fn(),
  fetchSummary: jest.fn(),
  fetchDashboard: jest.fn(),
}));

const emptyPage = {
  items: [],
  page: 1,
  page_size: 20,
  total: 0,
  total_pages: 0,
};

const draftShipment = {
  id: 1,
  shipment_number: "SH-0001",
  shipped_date: "2026-08-12",
  status: "DRAFT" as const,
  confirmed_at: null,
  created_at: "2026-08-12T00:00:00Z",
  updated_at: "2026-08-12T00:00:00Z",
  lines: [
    {
      id: 1,
      product_id: 10,
      product_code: "P-01",
      product_name: "煎茶製品",
      quantity: 1.25,
    },
  ],
};

const summary = {
  date_from: "2026-08-01",
  date_to: "2026-08-12",
  receipt_quantity: 10,
  manufacturing_quantity: 8,
  shipment_quantity: 3,
  current_raw_material_quantity: 20,
  current_product_quantity: 5,
  receipt_breakdown: [
    { code: "TL-01/V-01", name: "煎茶 / やぶきた", quantity: 10 },
  ],
  manufacturing_breakdown: [{ code: "P-01", name: "煎茶製品", quantity: 8 }],
  shipment_breakdown: [{ code: "P-01", name: "煎茶製品", quantity: 3 }],
};

beforeEach(() => {
  jest.resetAllMocks();
  jest.mocked(fetchMasters).mockResolvedValue([
    { id: 10, code: "P-01", name: "煎茶製品", is_active: true },
    { id: 11, code: "P-02", name: "玉露製品", is_active: true },
  ]);
});

test("原料在庫一覧のloadingとemptyを表示する", async () => {
  jest.mocked(fetchRawBalances).mockResolvedValue(emptyPage);
  renderApp("/inventory/raw-materials");
  expect(screen.getByRole("status")).toHaveTextContent("原料在庫を取得中");
  expect(await screen.findByText("原料在庫はありません")).toBeInTheDocument();
});

test("製品在庫一覧のerrorを表示する", async () => {
  jest.mocked(fetchProductBalances).mockRejectedValue(new Error("failed"));
  renderApp("/inventory/products");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "製品在庫の取得に失敗しました",
  );
});

test("製品在庫一覧のloadingとemptyを表示する", async () => {
  jest.mocked(fetchProductBalances).mockResolvedValue(emptyPage);
  renderApp("/inventory/products");
  expect(screen.getByRole("status")).toHaveTextContent("製品在庫を取得中");
  expect(await screen.findByText("製品在庫はありません")).toBeInTheDocument();
});

test("原料在庫一覧のerrorを表示する", async () => {
  jest.mocked(fetchRawBalances).mockRejectedValue(new Error("failed"));
  renderApp("/inventory/raw-materials");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "原料在庫の取得に失敗しました",
  );
});

test("製品在庫のページングをURLとAPIへ同期する", async () => {
  jest.mocked(fetchProductBalances).mockResolvedValue({
    items: [
      {
        id: 1,
        product_id: 10,
        product_code: "P-01",
        product_name: "煎茶製品",
        quantity: 2.5,
        unit: "kg",
        updated_at: "2026-08-12T00:00:00Z",
      },
    ],
    page: 1,
    page_size: 20,
    total: 21,
    total_pages: 2,
  });
  renderApp("/inventory/products?page=1&page_size=20");
  expect(
    await screen.findByText(/P-01 煎茶製品: 2.500 kg/),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "次へ" }));
  await waitFor(() =>
    expect(fetchProductBalances).toHaveBeenLastCalledWith(2, 20),
  );
});

test("在庫履歴の検索条件をURL経由でAPIへ渡す", async () => {
  jest.mocked(fetchInventoryTransactions).mockResolvedValue(emptyPage);
  renderApp("/inventory/transactions");
  fireEvent.change(screen.getByLabelText("在庫種別"), {
    target: { value: "PRODUCT" },
  });
  fireEvent.change(screen.getByLabelText("取引種別"), {
    target: { value: "SHIPMENT" },
  });
  fireEvent.change(screen.getByLabelText("product_id"), {
    target: { value: "10" },
  });
  fireEvent.change(screen.getByLabelText("開始日"), {
    target: { value: "2026-08-01" },
  });
  fireEvent.change(screen.getByLabelText("終了日"), {
    target: { value: "2026-08-12" },
  });
  fireEvent.click(screen.getByRole("button", { name: "検索" }));
  await waitFor(() =>
    expect(fetchInventoryTransactions).toHaveBeenLastCalledWith(
      expect.stringContaining("inventory_kind=PRODUCT"),
    ),
  );
  expect(fetchInventoryTransactions).toHaveBeenLastCalledWith(
    expect.stringContaining("transaction_type=SHIPMENT"),
  );
  expect(fetchInventoryTransactions).toHaveBeenLastCalledWith(
    expect.stringContaining("product_id=10"),
  );
  expect(screen.getByText("在庫履歴はありません")).toBeInTheDocument();
});

test("在庫履歴一覧のerrorを表示する", async () => {
  jest
    .mocked(fetchInventoryTransactions)
    .mockRejectedValue(new Error("failed"));
  renderApp("/inventory/transactions");
  expect(screen.getByRole("status")).toHaveTextContent("在庫履歴を取得中");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "在庫履歴の取得に失敗しました",
  );
});

async function fillShipmentForm() {
  expect(
    await screen.findByRole("heading", { name: "出荷登録" }),
  ).toBeInTheDocument();
  fireEvent.change(await screen.findByLabelText("出荷番号"), {
    target: { value: "SH-0100" },
  });
  fireEvent.change(screen.getByLabelText("出荷日"), {
    target: { value: "2026-08-20" },
  });
  fireEvent.change(screen.getAllByLabelText("製品")[0], {
    target: { value: "10" },
  });
  fireEvent.change(screen.getAllByLabelText("出荷数量 (kg)")[0], {
    target: { value: "1.250" },
  });
}

test("複数明細の出荷登録値をAPIへ渡し送信中はdisabledにする", async () => {
  jest
    .mocked(createShipment)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/shipments/new");
  await fillShipmentForm();
  fireEvent.click(screen.getByRole("button", { name: "明細追加" }));
  fireEvent.change(screen.getAllByLabelText("製品")[1], {
    target: { value: "11" },
  });
  fireEvent.change(screen.getAllByLabelText("出荷数量 (kg)")[1], {
    target: { value: "2.500" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() => expect(createShipment).toHaveBeenCalledTimes(1));
  expect(createShipment).toHaveBeenCalledWith({
    shipment_number: "SH-0100",
    shipped_date: "2026-08-20",
    lines: [
      { product_id: 10, quantity: "1.250" },
      { product_id: 11, quantity: "2.500" },
    ],
  });
  expect(screen.getByRole("button", { name: "保存中" })).toBeDisabled();
});

test("出荷登録失敗時に入力値を保持する", async () => {
  jest.mocked(createShipment).mockRejectedValue(new Error("failed"));
  renderApp("/shipments/new");
  await fillShipmentForm();
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "出荷の保存に失敗しました",
  );
  expect(screen.getByLabelText("出荷番号")).toHaveValue("SH-0100");
});

test("出荷登録の不正入力はAPIへ送信しない", async () => {
  renderApp("/shipments/new");
  fireEvent.click(await screen.findByRole("button", { name: "保存" }));
  await waitFor(() => expect(createShipment).not.toHaveBeenCalled());
});

test("出荷一覧のloadingとemptyを表示する", async () => {
  jest.mocked(fetchShipments).mockResolvedValue(emptyPage);
  renderApp("/shipments");
  expect(screen.getByRole("status")).toHaveTextContent("出荷を取得中");
  expect(await screen.findByText("出荷はありません")).toBeInTheDocument();
});

test("出荷一覧のerrorを表示する", async () => {
  jest.mocked(fetchShipments).mockRejectedValue(new Error("failed"));
  renderApp("/shipments");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "出荷の取得に失敗しました",
  );
});

test("出荷確定中は連続操作を防止する", async () => {
  jest.mocked(fetchShipment).mockResolvedValue(draftShipment);
  jest
    .mocked(confirmShipment)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/shipments/1");
  fireEvent.click(await screen.findByRole("button", { name: "出荷確定" }));
  expect(await screen.findByRole("button", { name: "確定中" })).toBeDisabled();
  expect(confirmShipment).toHaveBeenCalledWith(1);
});

test("出荷確定失敗を表示する", async () => {
  jest.mocked(fetchShipment).mockResolvedValue(draftShipment);
  jest.mocked(confirmShipment).mockRejectedValue(new Error("failed"));
  renderApp("/shipments/1");
  fireEvent.click(await screen.findByRole("button", { name: "出荷確定" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "出荷確定に失敗しました",
  );
});

test("出荷確定成功後に詳細を確定済みへ更新する", async () => {
  jest.mocked(fetchShipment).mockResolvedValue(draftShipment);
  jest.mocked(confirmShipment).mockResolvedValue({
    ...draftShipment,
    status: "CONFIRMED",
    confirmed_at: "2026-08-12T01:00:00Z",
  });
  renderApp("/shipments/1");
  fireEvent.click(await screen.findByRole("button", { name: "出荷確定" }));
  expect(
    await screen.findByText("確定済みのため読み取り専用です。"),
  ).toBeInTheDocument();
});

test("確定済み出荷を読み取り専用表示する", async () => {
  jest.mocked(fetchShipment).mockResolvedValue({
    ...draftShipment,
    status: "CONFIRMED",
    confirmed_at: "2026-08-12T01:00:00Z",
  });
  renderApp("/shipments/1");
  expect(
    await screen.findByText("確定済みのため読み取り専用です。"),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "出荷確定" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText("出荷番号")).not.toBeInTheDocument();
});

test("集計期間をURL同期し不正期間を表示する", async () => {
  jest.mocked(fetchSummary).mockResolvedValue(summary);
  renderApp("/reports?date_from=2026-08-01&date_to=2026-08-12");
  expect(await screen.findByText("入荷合計: 10.000 kg")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("開始日"), {
    target: { value: "2026-08-20" },
  });
  fireEvent.click(screen.getByRole("button", { name: "期間更新" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "開始日は終了日以前にしてください",
  );
});

test("ダッシュボードに元APIの値を表示する", async () => {
  jest.mocked(fetchDashboard).mockResolvedValue({
    date_from: "2026-07-14",
    date_to: "2026-08-12",
    manufacturing_status_counts: { DRAFT: 2, COMPLETED: 1 },
    raw_material_inventory: { item_count: 3, total_quantity: 20, unit: "kg" },
    product_inventory: { item_count: 2, total_quantity: 5, unit: "kg" },
    receipt_quantity: 10,
    manufacturing_quantity: 8,
    shipment_quantity: 3,
  });
  renderApp();
  expect(await screen.findByText("製造状態 DRAFT: 2件")).toBeInTheDocument();
  expect(screen.getByText(/原料在庫: 20.000 kg/)).toBeInTheDocument();
  expect(screen.getByText("期間確定出荷: 3.000 kg")).toBeInTheDocument();
});
