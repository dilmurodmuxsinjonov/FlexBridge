import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TelegramVerification from "./TelegramVerification";

const base = {
  challengeId: "c1",
  phone: "+998901112233",
  botUsername: "FlexBridgeBot",
  deepLink: "https://t.me/FlexBridgeBot?start=c1",
  verified: false,
};

describe("TelegramVerification", () => {
  it("LIVE: shows the deep link and steps, never the in-page bot emulator", () => {
    render(<TelegramVerification mode="LIVE" {...base} />);
    expect(screen.getByRole("link", { name: /Telegramda ochish/ })).toHaveAttribute("href", base.deepLink);
    expect(screen.getByText(base.phone)).toBeInTheDocument();
    expect(screen.queryByText(/Sinov rejimi/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /\/start/ })).not.toBeInTheDocument();
  });

  it("SIMULATION: labels the emulator as a test mode", () => {
    render(<TelegramVerification mode="SIMULATION" {...base} />);
    expect(screen.getByText(/Sinov rejimi/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /\/start/ })).toBeInTheDocument();
  });

  it("reports verification status", () => {
    render(<TelegramVerification mode="LIVE" {...base} verified />);
    expect(screen.getByRole("status")).toHaveTextContent("Raqam tasdiqlandi");
  });
});
