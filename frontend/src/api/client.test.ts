import { apiFetch } from "./client";
const mockFetch = jest.fn();

function responseMock(options: {
  ok: boolean;
  status: number;
  body: unknown;
}): Response {
  return {
    ok: options.ok,
    status: options.status,
    json: jest.fn().mockResolvedValue(options.body),
  } as unknown as Response;
}

beforeEach(() => {
  globalThis.fetch = mockFetch;
});

test("正常responseをJSONへ変換する", async () => {
  mockFetch.mockResolvedValue(
    responseMock({
      ok: true,
      status: 200,
      body: { status: "ok" },
    }),
  );

  await expect(apiFetch<{ status: string }>("/health")).resolves.toEqual({
    status: "ok",
  });
  expect(mockFetch).toHaveBeenCalledWith(
    "/api/v1/health",
    expect.objectContaining({
      headers: expect.objectContaining({ Accept: "application/json" }),
    }),
  );
});

test("統一APIエラーをApiErrorへ変換する", async () => {
  mockFetch.mockResolvedValue(
    responseMock({
      ok: false,
      status: 422,
      body: {
        code: "VALIDATION_ERROR",
        message: "入力内容を確認してください。",
        field_errors: [
          { field: "body.name", code: "required", message: "必須です。" },
        ],
      },
    }),
  );

  const request = apiFetch("/example");

  await expect(request).rejects.toMatchObject({
    name: "ApiError",
    status: 422,
    code: "VALIDATION_ERROR",
    message: "入力内容を確認してください。",
    fieldErrors: [
      { field: "body.name", code: "required", message: "必須です。" },
    ],
  });
});
