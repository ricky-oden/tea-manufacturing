import { screen } from "@testing-library/react";

import { fetchHealth } from "./api/health";
import { fetchDashboard } from "./api/phase4";
import { renderApp } from "./test/renderApp";

jest.mock("./api/health", () => ({
  fetchHealth: jest.fn(),
}));
jest.mock("./api/phase4", () => ({
  ...jest.requireActual("./api/phase4"),
  fetchDashboard: jest.fn(),
}));

const mockedFetchHealth = jest.mocked(fetchHealth);
const mockedFetchDashboard = jest.mocked(fetchDashboard);

beforeEach(() => {
  mockedFetchDashboard.mockReturnValue(new Promise(() => undefined));
});

test("Appがシステム名を表示する", () => {
  mockedFetchHealth.mockReturnValue(new Promise(() => undefined));

  renderApp();

  expect(
    screen.getByRole("heading", { name: "お茶製造管理システム" }),
  ).toBeInTheDocument();
});

test("health取得中を表示する", () => {
  mockedFetchHealth.mockReturnValue(new Promise(() => undefined));

  renderApp();

  expect(screen.getByText("backend health取得中")).toBeInTheDocument();
});

test("health成功を表示する", async () => {
  mockedFetchHealth.mockResolvedValue({ status: "ok" });

  renderApp();

  expect(await screen.findByText("backend health成功: ok")).toBeInTheDocument();
});

test("health失敗を表示する", async () => {
  mockedFetchHealth.mockRejectedValue(new Error("network unavailable"));

  renderApp();

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "backend health失敗",
  );
});
