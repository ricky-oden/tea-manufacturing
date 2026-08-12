import { screen } from "@testing-library/react";

import { fetchHealth } from "./api/health";
import { renderApp } from "./test/renderApp";

jest.mock("./api/health", () => ({
  fetchHealth: jest.fn(),
}));

const mockedFetchHealth = jest.mocked(fetchHealth);

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

  expect(screen.getByRole("status")).toHaveTextContent("backend health取得中");
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
