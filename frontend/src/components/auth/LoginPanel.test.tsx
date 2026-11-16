import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GraduationCap } from "lucide-react";

const api = vi.hoisted(() => ({
  fetchAuthMe: vi.fn(),
  loginUser: vi.fn(),
  verifyMfa: vi.fn(),
  logoutUser: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

const nav = vi.hoisted(() => ({ replace: vi.fn(), refresh: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace, refresh: nav.refresh, push: nav.replace }),
  useSearchParams: () => nav.params,
}));

import LoginPanel, { type LoginPanelConfig } from "./LoginPanel";

const studentConfig: LoginPanelConfig = {
  portal: "CANDIDATE",
  tone: "sky",
  icon: GraduationCap,
  badge: "Talaba kirishi",
  audience: "talaba",
  title: "Talaba kabinetiga kirish",
  subtitle: "Rezyume va arizalar",
  identifierPlaceholder: "talaba@otm.uz",
  submitLabel: "Kirish",
  home: "/nomzod",
  redirectPrefixes: ["/nomzod", "/ishlar"],
  register: { href: "/talaba/royxatdan-otish", label: "Ro‘yxatdan o‘tish" },
  asideTitle: "Talabalar uchun",
  asideText: "",
  features: [],
};

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText("Telefon raqam yoki elektron pochta"), { target: { value: "ali@otm.uz" } });
  fireEvent.change(screen.getByLabelText("Parol"), { target: { value: "secret-pass" } });
  fireEvent.click(screen.getByRole("button", { name: /^Kirish/ }));
}

describe("LoginPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    nav.params = new URLSearchParams();
    api.fetchAuthMe.mockResolvedValue(null);
  });

  it("shows a human message instead of a raw backend code", async () => {
    api.loginUser.mockResolvedValue({ ok: false, error: "INVALID_CREDENTIALS" });
    render(<LoginPanel config={studentConfig} />);
    fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent("Telefon/pochta yoki parol noto‘g‘ri");
    expect(screen.queryByText("INVALID_CREDENTIALS")).not.toBeInTheDocument();
    expect(api.loginUser).toHaveBeenCalledWith("ali@otm.uz", "secret-pass", undefined, "CANDIDATE");
  });

  it("asks for the authenticator code and submits it automatically at six digits", async () => {
    api.loginUser.mockResolvedValue({ ok: true, mfa_required: true, mfa_ticket: "t-1", expires_in: 300 });
    api.verifyMfa.mockResolvedValue({ ok: true, user_id: "u", roles: ["CANDIDATE"] });
    render(<LoginPanel config={studentConfig} />);
    fillAndSubmit();
    const code = await screen.findByLabelText("6 xonali kod");
    fireEvent.change(code, { target: { value: "12a3456" } });
    await waitFor(() => expect(api.verifyMfa).toHaveBeenCalledWith("t-1", "123456", "CANDIDATE"));
    await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/nomzod"));
  });

  it("honours a safe redirect inside the portal and ignores foreign ones", async () => {
    api.loginUser.mockResolvedValue({ ok: true, user_id: "u", roles: ["CANDIDATE"] });
    nav.params = new URLSearchParams("redirect=/ishlar/abc");
    const { unmount } = render(<LoginPanel config={studentConfig} />);
    fillAndSubmit();
    await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/ishlar/abc"));
    unmount();

    nav.replace.mockClear();
    nav.params = new URLSearchParams("redirect=//evil.example/x");
    render(<LoginPanel config={studentConfig} />);
    fillAndSubmit();
    await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/nomzod"));
  });

  it("explains a signed-in account of another role and offers to switch", async () => {
    api.fetchAuthMe.mockResolvedValue({ user_id: "u", roles: ["HR"] });
    api.logoutUser.mockResolvedValue(undefined);
    render(<LoginPanel config={studentConfig} />);
    expect(await screen.findByText("Siz boshqa hisob bilan kirgansiz")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Korxona Kabinetiga o‘tish/ })).toHaveAttribute("href", "/employer");
    fireEvent.click(screen.getByRole("button", { name: /Chiqish va boshqa hisob/ }));
    await waitFor(() => expect(api.logoutUser).toHaveBeenCalled());
    expect(await screen.findByText("Talaba kabinetiga kirish")).toBeInTheDocument();
  });

  it("toggles password visibility with an accessible button", () => {
    render(<LoginPanel config={studentConfig} />);
    const pw = screen.getByLabelText("Parol");
    expect(pw).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "Parolni ko‘rsatish" }));
    expect(pw).toHaveAttribute("type", "text");
  });
});
