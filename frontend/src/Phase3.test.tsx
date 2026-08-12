import { fireEvent, screen, waitFor } from "@testing-library/react";

import { fetchMasters, fetchOrder } from "./api/manufacturing";
import {
  createEquipment,
  createReceipt,
  fetchEquipment,
  fetchReceipt,
  fetchProcesses,
  fetchReceipts,
  updateEquipment,
  updateProcess,
} from "./api/phase3";
import { renderApp } from "./test/renderApp";

jest.mock("./api/manufacturing", () => ({
  fetchOrders: jest.fn(),
  fetchOrder: jest.fn(),
  transitionOrder: jest.fn(),
  fetchMasters: jest.fn(),
  createOrder: jest.fn(),
}));
jest.mock("./api/phase3", () => ({
  ...jest.requireActual("./api/phase3"),
  fetchReceipts: jest.fn(),
  fetchReceipt: jest.fn(),
  createReceipt: jest.fn(),
  fetchProcesses: jest.fn(),
  updateProcess: jest.fn(),
  fetchEquipment: jest.fn(),
  createEquipment: jest.fn(),
  updateEquipment: jest.fn(),
}));

const masterData = {
  suppliers: [{ id: 1, code: "S-01", name: "茶園A", is_active: true }],
  "tea-leaves": [
    { id: 2, code: "TL-01", name: "煎茶", is_active: true },
    { id: 3, code: "TL-02", name: "玉露", is_active: true },
  ],
  varieties: [{ id: 4, code: "V-01", name: "やぶきた", is_active: true }],
  equipment: [],
  products: [],
};

const order = {
  id: 1,
  order_number: "MO-0001",
  product_id: 1,
  product_name: "煎茶製品",
  planned_quantity: 2.5,
  planned_date: "2026-08-12",
  equipment_id: 1,
  equipment_name: "蒸機",
  status: "IN_PROGRESS" as const,
  started_at: "2026-08-12T01:00:00Z",
  completed_at: null,
  materials: [],
};

const processes = [
  {
    id: 1,
    manufacturing_order_id: 1,
    sequence: 1,
    process_code: "STEAMING",
    process_name: "蒸熱",
    status: "PENDING" as const,
    equipment_id: null,
    equipment_name: null,
    started_at: null,
    completed_at: null,
    result_note: null,
  },
  {
    id: 2,
    manufacturing_order_id: 1,
    sequence: 2,
    process_code: "ROLLING",
    process_name: "揉捻",
    status: "IN_PROGRESS" as const,
    equipment_id: null,
    equipment_name: null,
    started_at: "2026-08-12T01:00:00Z",
    completed_at: null,
    result_note: null,
  },
  {
    id: 3,
    manufacturing_order_id: 1,
    sequence: 3,
    process_code: "DRYING",
    process_name: "乾燥",
    status: "COMPLETED" as const,
    equipment_id: null,
    equipment_name: null,
    started_at: "2026-08-12T01:00:00Z",
    completed_at: "2026-08-12T02:00:00Z",
    result_note: null,
  },
];

beforeEach(() => {
  jest.resetAllMocks();
  jest
    .mocked(fetchMasters)
    .mockImplementation(async (resource) => masterData[resource]);
});

test("原料入荷一覧のloadingとemptyを表示する", async () => {
  jest.mocked(fetchReceipts).mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  });
  renderApp("/raw-material-receipts");
  expect(screen.getByRole("status")).toHaveTextContent("原料入荷を取得中");
  expect(await screen.findByText("原料入荷はありません")).toBeInTheDocument();
});

test("原料入荷一覧のAPI失敗を表示する", async () => {
  jest.mocked(fetchReceipts).mockRejectedValue(new Error("failed"));
  renderApp("/raw-material-receipts");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "原料入荷の取得に失敗しました",
  );
});

test("原料入荷詳細を表示する", async () => {
  jest.mocked(fetchReceipt).mockResolvedValue({
    id: 1,
    receipt_number: "RC-0001",
    received_date: "2026-08-12",
    supplier_id: 1,
    supplier_name: "茶園A",
    created_at: "2026-08-12T00:00:00Z",
    lines: [
      {
        id: 1,
        tea_leaf_id: 2,
        tea_leaf_name: "煎茶",
        variety_id: 4,
        variety_name: "やぶきた",
        quantity: 1.25,
      },
    ],
  });
  renderApp("/raw-material-receipts/1");
  expect(screen.getByRole("status")).toHaveTextContent("原料入荷詳細を取得中");
  expect(await screen.findByText("RC-0001")).toBeInTheDocument();
  expect(screen.getByText(/煎茶 \/ やぶきた \/ 1.250 kg/)).toBeInTheDocument();
});

async function fillReceiptForm() {
  expect(
    await screen.findByRole("heading", { name: "原料入荷登録" }),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("入荷番号"), {
    target: { value: "RC-0100" },
  });
  fireEvent.change(screen.getByLabelText("入荷日"), {
    target: { value: "2026-08-20" },
  });
  fireEvent.change(screen.getByLabelText("仕入先"), { target: { value: "1" } });
  fireEvent.change(screen.getAllByLabelText("茶葉")[0], {
    target: { value: "2" },
  });
  fireEvent.change(screen.getAllByLabelText("品種")[0], {
    target: { value: "4" },
  });
  fireEvent.change(screen.getAllByLabelText("入荷数量 (kg)")[0], {
    target: { value: "1.250" },
  });
}

test("複数明細をAPIへ渡し送信中は登録をdisabledにする", async () => {
  jest
    .mocked(createReceipt)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/raw-material-receipts/new");
  await fillReceiptForm();
  fireEvent.click(screen.getByRole("button", { name: "明細追加" }));
  fireEvent.change(screen.getAllByLabelText("茶葉")[1], {
    target: { value: "3" },
  });
  fireEvent.change(screen.getAllByLabelText("品種")[1], {
    target: { value: "4" },
  });
  fireEvent.change(screen.getAllByLabelText("入荷数量 (kg)")[1], {
    target: { value: "2.500" },
  });
  fireEvent.click(screen.getByRole("button", { name: "入荷登録" }));

  await waitFor(() => expect(createReceipt).toHaveBeenCalledTimes(1));
  expect(jest.mocked(createReceipt).mock.calls[0][0]).toEqual({
    receipt_number: "RC-0100",
    received_date: "2026-08-20",
    supplier_id: 1,
    lines: [
      { tea_leaf_id: 2, variety_id: 4, quantity: "1.250" },
      { tea_leaf_id: 3, variety_id: 4, quantity: "2.500" },
    ],
  });
  expect(screen.getByRole("button", { name: "登録中" })).toBeDisabled();
});

test("入荷フォームの不正入力は送信しない", async () => {
  renderApp("/raw-material-receipts/new");
  fireEvent.click(await screen.findByRole("button", { name: "入荷登録" }));
  await waitFor(() => expect(createReceipt).not.toHaveBeenCalled());
});

test("入荷API失敗時に入力を保持する", async () => {
  jest.mocked(createReceipt).mockRejectedValue(new Error("failed"));
  renderApp("/raw-material-receipts/new");
  await fillReceiptForm();
  fireEvent.click(screen.getByRole("button", { name: "入荷登録" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "原料入荷の登録に失敗しました",
  );
  expect(screen.getByLabelText("入荷番号")).toHaveValue("RC-0100");
});

test("工程状態別ボタンを表示し操作中は連続操作を防ぐ", async () => {
  jest.mocked(fetchOrder).mockResolvedValue(order);
  jest.mocked(fetchProcesses).mockResolvedValue(processes);
  jest
    .mocked(updateProcess)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/manufacturing-orders/1");
  expect(await screen.findByText(/蒸熱 \/ PENDING/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "工程開始" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "工程完了" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "工程開始" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "工程開始" })).toBeDisabled(),
  );
  expect(screen.getByRole("button", { name: "工程完了" })).toBeDisabled();
});

test("工程操作失敗を表示する", async () => {
  jest.mocked(fetchOrder).mockResolvedValue(order);
  jest.mocked(fetchProcesses).mockResolvedValue(processes);
  jest.mocked(updateProcess).mockRejectedValue(new Error("failed"));
  renderApp("/manufacturing-orders/1");
  fireEvent.click(await screen.findByRole("button", { name: "工程開始" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "工程操作に失敗しました",
  );
});

test("設備一覧のemptyと登録中表示を扱う", async () => {
  jest.mocked(fetchEquipment).mockResolvedValue([]);
  jest
    .mocked(createEquipment)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/equipment");
  expect(await screen.findByText("設備はありません")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("設備コード"), {
    target: { value: "EQ-10" },
  });
  fireEvent.change(screen.getByLabelText("設備名"), {
    target: { value: "乾燥機" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() => expect(createEquipment).toHaveBeenCalledTimes(1));
  expect(screen.getByRole("button", { name: "保存中" })).toBeDisabled();
});

test("設備編集と有効無効後に一覧を再取得する", async () => {
  const equipment = { id: 10, code: "EQ-10", name: "乾燥機", is_active: true };
  jest.mocked(fetchEquipment).mockResolvedValue([equipment]);
  jest.mocked(updateEquipment).mockResolvedValue(equipment);
  renderApp("/equipment");
  fireEvent.click(await screen.findByRole("button", { name: "編集" }));
  fireEvent.change(screen.getByLabelText("設備名"), {
    target: { value: "乾燥機更新" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() =>
    expect(updateEquipment).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ name: "乾燥機更新", is_active: true }),
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "無効にする" }));
  await waitFor(() => expect(updateEquipment).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(fetchEquipment).toHaveBeenCalledTimes(3));
});
