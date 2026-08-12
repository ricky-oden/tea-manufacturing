import { fireEvent, screen, waitFor } from "@testing-library/react";

import {
  createOrder,
  fetchMasters,
  fetchOrder,
  fetchOrders,
  transitionOrder,
} from "./api/manufacturing";
import { renderApp } from "./test/renderApp";

jest.mock("./api/manufacturing", () => ({
  fetchOrders: jest.fn(),
  fetchOrder: jest.fn(),
  transitionOrder: jest.fn(),
  fetchMasters: jest.fn(),
  createOrder: jest.fn(),
}));

const order = {
  id: 1,
  order_number: "MO-0001",
  product_id: 1,
  product_name: "煎茶製品",
  planned_quantity: 2.5,
  planned_date: "2026-08-12",
  equipment_id: 1,
  equipment_name: "蒸機",
  status: "ISSUED" as const,
  started_at: null,
  completed_at: null,
  materials: [],
};

const masters = {
  products: [{ id: 1, code: "P-01", name: "煎茶製品", is_active: true }],
  equipment: [{ id: 2, code: "EQ-01", name: "蒸機", is_active: true }],
  "tea-leaves": [{ id: 3, code: "TL-01", name: "煎茶", is_active: true }],
  varieties: [{ id: 4, code: "V-01", name: "やぶきた", is_active: true }],
};

beforeEach(() => {
  jest.resetAllMocks();
});

function mockMasterResponses() {
  jest
    .mocked(fetchMasters)
    .mockImplementation(async (resource) => masters[resource]);
}

async function fillOrderForm() {
  expect(
    await screen.findByRole("heading", { name: "製造指示登録" }),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("製造指示番号"), {
    target: { value: "MO-0100" },
  });
  fireEvent.change(screen.getByLabelText("製品"), { target: { value: "1" } });
  fireEvent.change(screen.getByLabelText("予定数量 (kg)"), {
    target: { value: "2.500" },
  });
  fireEvent.change(screen.getByLabelText("予定日"), {
    target: { value: "2026-08-20" },
  });
  fireEvent.change(screen.getByLabelText("設備"), { target: { value: "2" } });
  fireEvent.change(screen.getByLabelText("茶葉"), { target: { value: "3" } });
  fireEvent.change(screen.getByLabelText("品種"), { target: { value: "4" } });
  fireEvent.change(screen.getByLabelText("原料予定使用量 (kg)"), {
    target: { value: "3.000" },
  });
}

test("製造指示一覧のloadingとemptyを表示する", async () => {
  jest.mocked(fetchOrders).mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  });
  renderApp("/manufacturing-orders");
  expect(screen.getByRole("status")).toHaveTextContent("製造指示を取得中");
  expect(await screen.findByText("製造指示はありません")).toBeInTheDocument();
});

test("製造指示一覧のAPI失敗を表示する", async () => {
  jest.mocked(fetchOrders).mockRejectedValue(new Error("failed"));
  renderApp("/manufacturing-orders");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "製造指示の取得に失敗しました",
  );
});

test("指示済み詳細は製造開始と取消を表示する", async () => {
  jest.mocked(fetchOrder).mockResolvedValue(order);
  jest
    .mocked(transitionOrder)
    .mockResolvedValue({ ...order, status: "IN_PROGRESS" });
  renderApp("/manufacturing-orders/1");
  expect(await screen.findByText("状態: ISSUED")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "製造開始" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "取消" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "製造開始" }));
  await waitFor(() => expect(transitionOrder).toHaveBeenCalledWith(1, "start"));
});

test("完了済み詳細は読み取り専用になる", async () => {
  jest.mocked(fetchOrder).mockResolvedValue({ ...order, status: "COMPLETED" });
  renderApp("/manufacturing-orders/1");
  expect(
    await screen.findByText("完了・取消済みのため読み取り専用です。"),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "製造開始" }),
  ).not.toBeInTheDocument();
});

test("製造指示登録値をAPIへ渡し送信中は連続登録を防ぐ", async () => {
  mockMasterResponses();
  jest
    .mocked(createOrder)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/manufacturing-orders/new");
  await fillOrderForm();

  fireEvent.click(screen.getByRole("button", { name: "下書き登録" }));

  await waitFor(() => expect(createOrder).toHaveBeenCalledTimes(1));
  expect(jest.mocked(createOrder).mock.calls[0][0]).toEqual({
    order_number: "MO-0100",
    product_id: 1,
    planned_quantity: "2.500",
    planned_date: "2026-08-20",
    equipment_id: 2,
    materials: [
      {
        tea_leaf_id: 3,
        variety_id: 4,
        planned_quantity: "3.000",
      },
    ],
  });
  expect(screen.getByRole("button", { name: "登録中" })).toBeDisabled();
});

test("登録API失敗時にエラーと入力値を保持する", async () => {
  mockMasterResponses();
  jest.mocked(createOrder).mockRejectedValue(new Error("failed"));
  renderApp("/manufacturing-orders/new");
  await fillOrderForm();

  fireEvent.click(screen.getByRole("button", { name: "下書き登録" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "登録に失敗しました",
  );
  expect(screen.getByLabelText("製造指示番号")).toHaveValue("MO-0100");
  expect(screen.getByLabelText("予定数量 (kg)")).toHaveValue(2.5);
});

test("製造中詳細は製造完了だけを表示する", async () => {
  jest
    .mocked(fetchOrder)
    .mockResolvedValue({ ...order, status: "IN_PROGRESS" });
  renderApp("/manufacturing-orders/1");
  expect(await screen.findByRole("button", { name: "製造完了" })).toBeEnabled();
  expect(
    screen.queryByRole("button", { name: "指示確定" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "製造開始" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "取消" }),
  ).not.toBeInTheDocument();
});

test("状態操作中はボタンをdisabledにして連続操作を防ぐ", async () => {
  jest
    .mocked(fetchOrder)
    .mockResolvedValue({ ...order, status: "IN_PROGRESS" });
  jest
    .mocked(transitionOrder)
    .mockImplementation(() => new Promise(() => undefined));
  renderApp("/manufacturing-orders/1");
  fireEvent.click(await screen.findByRole("button", { name: "製造完了" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "製造完了" })).toBeDisabled(),
  );
  expect(transitionOrder).toHaveBeenCalledTimes(1);
});

test("状態操作失敗時にエラーを表示する", async () => {
  jest
    .mocked(fetchOrder)
    .mockResolvedValue({ ...order, status: "IN_PROGRESS" });
  jest.mocked(transitionOrder).mockRejectedValue(new Error("failed"));
  renderApp("/manufacturing-orders/1");
  fireEvent.click(await screen.findByRole("button", { name: "製造完了" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "状態操作に失敗しました",
  );
});
