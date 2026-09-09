import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("authenticated report downloads", () => {
  beforeEach(() => {
    sessionStorage.setItem("access_token", "demo-token");
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(new Blob(["pdf"]), {
            status: 200,
            headers: { "Content-Type": "application/pdf" },
          }),
        ),
    );
    URL.createObjectURL = vi.fn(() => "blob:report");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });
  it("sends the JWT and downloads the PDF", async () => {
    await api.downloadReport("test-1", "pdf");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/reports/test-1.pdf"),
      expect.objectContaining({
        headers: { Authorization: "Bearer demo-token" },
      }),
    );
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled();
  });
});
