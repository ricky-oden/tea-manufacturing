import { fireEvent, screen, waitFor } from "@testing-library/react";

import {
  createMaster,
  fetchMasterPage,
  fetchMasters,
  fetchOrder,
  fetchOrders,
  updateMaster,
  updateOrder,
} from "./api/manufacturing";
import { fetchProcesses } from "./api/phase3";
import { renderApp } from "./test/renderApp";

jest.mock("./api/manufacturing", () => ({
  fetchOrders: jest.fn(),
  fetchOrder: jest.fn(),
  transitionOrder: jest.fn(),
  fetchMasters: jest.fn(),
  fetchMasterPage: jest.fn(),
  createMaster: jest.fn(),
  updateMaster: jest.fn(),
  createOrder: jest.fn(),
  updateOrder: jest.fn(),
}));
jest.mock("./api/phase3", () => ({
  ...jest.requireActual("./api/phase3"),
  fetchProcesses: jest.fn(),
  updateProcess: jest.fn(),
}));

const master = { id: 1, code: "TL-01", name: "煎茶", is_active: true };
const order = {
  id: 1,
  order_number: "MO-01",
  product_id: 4,
  product_name: "煎茶製品",
  planned_quantity: 2.5,
  planned_date: "2026-08-12",
  equipment_id: 3,
  equipment_name: "蒸機",
  status: "DRAFT" as const,
  started_at: null,
  completed_at: null,
  materials: [
    {
      id: 1,
      tea_leaf_id: 1,
      tea_leaf_name: "煎茶",
      variety_id: 2,
      variety_name: "やぶきた",
      planned_quantity: 3,
    },
  ],
  processes: [],
  inventory_transactions: [
    {
      id: 1,
      inventory_kind: "RAW_MATERIAL" as const,
      transaction_type: "MANUFACTURING_CONSUMPTION",
      quantity_delta: -3,
      balance_after: 7,
      occurred_at: "2026-08-12T00:00:00Z",
    },
  ],
};

beforeEach(() => {
  jest.resetAllMocks();
  jest.mocked(fetchProcesses).mockResolvedValue([]);
  jest.mocked(fetchMasters).mockImplementation(async (resource) => {
    const data = {
      "tea-leaves": [master],
      varieties: [{ id: 2, code: "VR-01", name: "やぶきた", is_active: true }],
      equipment: [{ id: 3, code: "EQ-01", name: "蒸機", is_active: true }],
      products: [{ id: 4, code: "PR-01", name: "煎茶製品", is_active: true }],
      suppliers: [],
    };
    return data[resource];
  });
});

test("マスタ一覧のloadingとemptyを表示する", async () => {
  jest.mocked(fetchMasterPage).mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  });
  renderApp("/masters/tea-leaves");
  expect(screen.getByRole("status")).toHaveTextContent("茶葉を取得中");
  expect(await screen.findByText("茶葉はありません")).toBeInTheDocument();
});

test("マスタを登録し送信中は連続操作を防ぐ", async () => {
  jest.mocked(fetchMasterPage).mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  });
  jest
    .mocked(createMaster)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/masters/tea-leaves");
  await screen.findByText("茶葉はありません");
  fireEvent.change(screen.getByLabelText("茶葉コード"), {
    target: { value: "TL-02" },
  });
  fireEvent.change(screen.getByLabelText("茶葉名"), {
    target: { value: "玉露" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() =>
    expect(createMaster).toHaveBeenCalledWith("tea-leaves", {
      code: "TL-02",
      name: "玉露",
      is_active: true,
    }),
  );
  expect(screen.getByRole("button", { name: "保存中" })).toBeDisabled();
});

test("マスタ詳細から編集と有効無効操作を行う", async () => {
  jest.mocked(fetchMasterPage).mockResolvedValue({
    items: [master],
    page: 1,
    page_size: 20,
    total: 1,
    total_pages: 1,
  });
  jest.mocked(updateMaster).mockResolvedValue({ ...master, is_active: false });
  renderApp("/masters/tea-leaves");
  expect(await screen.findByText(/TL-01/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "編集" }));
  expect(screen.getByRole("heading", { name: "茶葉編集" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "無効にする" }));
  await waitFor(() =>
    expect(updateMaster).toHaveBeenCalledWith("tea-leaves", 1, {
      code: "TL-01",
      name: "煎茶",
      is_active: false,
      variety_id: undefined,
    }),
  );
});

test("製造指示の絞り込み条件をAPIへ渡す", async () => {
  jest.mocked(fetchOrders).mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  });
  renderApp(
    "/manufacturing-orders?status=DRAFT&product_id=4&planned_date_from=2026-08-01&planned_date_to=2026-08-31",
  );
  await screen.findByText("製造指示はありません");
  expect(fetchOrders).toHaveBeenCalledWith(1, 20, {
    status: "DRAFT",
    product_id: "4",
    planned_date_from: "2026-08-01",
    planned_date_to: "2026-08-31",
  });
});

test("下書き編集フォームを初期化して更新APIへ渡す", async () => {
  jest.mocked(fetchOrder).mockResolvedValue(order);
  jest
    .mocked(updateOrder)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/manufacturing-orders/1/edit");
  expect(
    await screen.findByRole("heading", { name: "製造指示編集" }),
  ).toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getByLabelText("製造指示番号")).toHaveValue("MO-01"),
  );
  fireEvent.change(screen.getByLabelText("製造指示番号"), {
    target: { value: "MO-EDIT" },
  });
  fireEvent.click(screen.getByRole("button", { name: "下書き保存" }));
  await waitFor(() => expect(updateOrder).toHaveBeenCalled());
  expect(screen.getByRole("button", { name: "保存中" })).toBeDisabled();
});

test("製造指示詳細に原料設備工程と関連在庫履歴を表示する", async () => {
  jest.mocked(fetchOrder).mockResolvedValue(order);
  renderApp("/manufacturing-orders/1");
  expect(await screen.findByText("設備: 蒸機")).toBeInTheDocument();
  expect(screen.getByText(/煎茶 \/ やぶきた \/ 3.000 kg/)).toBeInTheDocument();
  expect(
    screen.getByText(/MANUFACTURING_CONSUMPTION \/ -3.000 kg/),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "下書き編集" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "製造工程" })).toBeInTheDocument();
});
