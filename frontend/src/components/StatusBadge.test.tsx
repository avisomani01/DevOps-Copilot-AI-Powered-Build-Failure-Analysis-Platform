import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders a readable upload status", () => {
    render(<StatusBadge value="UPLOADED" />);
    expect(screen.getByText("UPLOADED")).toBeTruthy();
  });
});
