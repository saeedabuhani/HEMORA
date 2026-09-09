import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge, Disclaimer } from "./components";
describe("medical UI", () => {
  it("renders Hebrew status text", () => {
    render(<StatusBadge status="LOW" />);
    expect(screen.getByText("נמוך")).toBeInTheDocument();
  });
  it("keeps the medical disclaimer visible", () => {
    render(<Disclaimer />);
    expect(screen.getByText(/אינה מהווה אבחנה רפואית/)).toBeInTheDocument();
  });
});
