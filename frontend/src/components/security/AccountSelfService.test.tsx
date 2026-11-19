import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AccountProfileAndPasswordPanel from "./AccountProfileAndPasswordPanel";
import AccountSecurityWorkspace from "./AccountSecurityWorkspace";
import ContactsPanel from "./ContactsPanel";

const navMock = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: navMock.push, replace: navMock.replace, refresh: navMock.refresh }),
}));

const CNT_1 = "11111111-1111-4111-8111-111111111111";
const CNT_2 = "22222222-2222-4222-8222-222222222222";

describe("AccountSelfService UI (LOG-208)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("updates display name and changes password with validation", async () => {
    const calls: { url: string; method: string; body?: Record<string, unknown> }[] = [];
    const authEventSpy = vi.fn();
    window.addEventListener("flexbridge:auth-changed", authEventSpy);

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });

      if (url === "/api/bff/me/profile" && method === "PATCH") {
        return new Response(
          JSON.stringify({ ok: true, user_id: "u-emp", display_name: "Dilnoza HR Director" }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/me/security/password" && method === "POST") {
        return new Response(
          JSON.stringify({
            ok: true,
            password_updated: true,
            revoked_other_sessions: 1,
            reauthentication_required: false,
          }),
          { status: 200 }
        );
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onDisplayNameUpdated = vi.fn();
    const onPasswordChanged = vi.fn();

    render(
      <AccountProfileAndPasswordPanel
        displayName="Demo Employer"
        roles={["CANDIDATE", "OWNER", "EMPLOYER"]}
        totpEnabled={true}
        onDisplayNameUpdated={onDisplayNameUpdated}
        onPasswordChanged={onPasswordChanged}
      />
    );

    // 1. Update display name
    fireEvent.change(screen.getByLabelText(/To‘liq ism-familiya/i), {
      target: { value: "Dilnoza HR Director" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Nomni saqlash/i }));

    await waitFor(() =>
      expect(screen.getByText(/Akkaunt nomi muvaffaqiyatli yangilandi/i)).toBeTruthy()
    );
    expect(onDisplayNameUpdated).toHaveBeenCalledWith("Dilnoza HR Director");
    expect(authEventSpy).toHaveBeenCalled();

    // 2. Password mismatch validation blocks network request
    fireEvent.change(screen.getByLabelText(/Joriy parol \*/i), {
      target: { value: "CurrentPass123!" },
    });
    fireEvent.change(screen.getByLabelText(/Yangi parol \(kamida 12 belgi\) \*/i), {
      target: { value: "NewStrongPass2026!" },
    });
    fireEvent.change(screen.getByLabelText(/Yangi parolni tasdiqlash \*/i), {
      target: { value: "MismatchPass2026!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Parolni yangilash/i }));

    expect(screen.getByText(/mos kelmadi/i)).toBeTruthy();
    expect(calls.some((c) => c.url === "/api/bff/me/security/password")).toBe(false);

    // 3. Valid password change sends current + new + totp_code
    fireEvent.change(screen.getByLabelText(/Yangi parolni tasdiqlash \*/i), {
      target: { value: "NewStrongPass2026!" },
    });
    fireEvent.change(screen.getByLabelText(/6 xonali TOTP kodi/i), {
      target: { value: "654321" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Parolni yangilash/i }));

    await waitFor(() =>
      expect(screen.getByText(/1 ta faol sessiya yakunlandi/i)).toBeTruthy()
    );
    const pwCall = calls.find((c) => c.url === "/api/bff/me/security/password");
    expect(pwCall?.body).toEqual({
      current_password: "CurrentPass123!",
      new_password: "NewStrongPass2026!",
      totp_code: "654321",
    });
    expect(onPasswordChanged).toHaveBeenCalledTimes(1);

    window.removeEventListener("flexbridge:auth-changed", authEventSpy);
  });

  it("switches primary login contact and removes secondary contact with step-up, protecting last contact", async () => {
    let contactList = [
      { id: CNT_1, channel: "PHONE", masked_destination: "+99890***1234", is_primary: true },
      { id: CNT_2, channel: "EMAIL", masked_destination: "h***@firm.uz", is_primary: false },
    ];
    const calls: { url: string; method: string }[] = [];

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      calls.push({ url, method });

      if (url === "/api/bff/me/contacts" && method === "GET") {
        return new Response(JSON.stringify({ ok: true, items: contactList }), { status: 200 });
      }
      if (url === "/api/auth/options") {
        return new Response(JSON.stringify({ ok: true, telegram_mode: "DISABLED" }), { status: 200 });
      }
      if (url === `/api/bff/me/contacts/${CNT_2}/primary` && method === "PATCH") {
        contactList = [
          { id: CNT_1, channel: "PHONE", masked_destination: "+99890***1234", is_primary: false },
          { id: CNT_2, channel: "EMAIL", masked_destination: "h***@firm.uz", is_primary: true },
        ];
        return new Response(
          JSON.stringify({ ok: true, contact_id: CNT_2, channel: "EMAIL", is_primary: true }),
          { status: 200 }
        );
      }
      if (url === `/api/bff/me/contacts/${CNT_1}` && method === "DELETE") {
        contactList = [{ id: CNT_2, channel: "EMAIL", masked_destination: "h***@firm.uz", is_primary: true }];
        return new Response(
          JSON.stringify({ ok: true, contact_id: CNT_1, removed: true, promoted_primary_contact_id: null }),
          { status: 200 }
        );
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ContactsPanel totpEnabled={false} />);

    await waitFor(() => expect(screen.getByText("h***@firm.uz")).toBeTruthy());

    // Switch primary to secondary email
    fireEvent.click(screen.getByRole("button", { name: /Asosiy qilish/i }));
    fireEvent.change(screen.getByLabelText(/Aloqa amali uchun joriy parol/i), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Asosiy qilib tasdiqlash/i }));

    await waitFor(() =>
      expect(screen.getByText(/h\*\*\*@firm\.uz asosiy kirish aloqasi sifatida belgilandi/i)).toBeTruthy()
    );
    expect(calls.some((c) => c.url === `/api/bff/me/contacts/${CNT_2}/primary` && c.method === "PATCH")).toBe(true);

    // Delete old phone -> only email remains -> delete controls disappear and single-contact label shows
    const deleteButtons = screen.getAllByRole("button", { name: /O‘chirish/i });
    fireEvent.click(deleteButtons[0]);
    fireEvent.change(screen.getByLabelText(/Aloqa amali uchun joriy parol/i), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /O‘chirishni tasdiqlash/i }));

    await waitFor(() => expect(screen.getByText(/Yagona kirish manzili/i)).toBeTruthy());
    expect(screen.queryByRole("button", { name: /O‘chirish/i })).toBeNull();
  });

  it("renders universal /hisob workspace for non-student EMPLOYER/OWNER role without restriction", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/auth/me") {
        return new Response(
          JSON.stringify({
            ok: true,
            user: {
              user_id: "u-employer",
              session_id: "sess-1",
              roles: ["CANDIDATE", "OWNER", "EMPLOYER"],
              display_name: "Korxona Rahbari",
            },
          }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/me/security") {
        return new Response(
          JSON.stringify({
            ok: true,
            user_id: "u-employer",
            totp_enabled: false,
            recovery_codes_count: 0,
            passkeys_count: 0,
            passkeys: [],
            current_session_id: "sess-1",
            sessions: [],
          }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/me/contacts") {
        return new Response(
          JSON.stringify({
            ok: true,
            items: [{ id: CNT_1, channel: "EMAIL", masked_destination: "o***@uz.com", is_primary: true }],
          }),
          { status: 200 }
        );
      }
      if (url === "/api/auth/options") {
        return new Response(JSON.stringify({ ok: true, telegram_mode: "DISABLED" }), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AccountSecurityWorkspace mode="universal" />);

    await waitFor(() => expect(screen.getByDisplayValue("Korxona Rahbari")).toBeTruthy());
    const employerBackLink = screen.getByRole("link", { name: /Korxona Kabineti/i });
    expect(employerBackLink).toHaveAttribute("href", "/employer");
    expect(screen.getByRole("heading", { name: /Hisob va xavfsizlik/i })).toBeTruthy();
    expect(screen.getByText(/Parolni almashtirish/i)).toBeTruthy();
    expect(screen.getByText(/o\*\*\*@uz\.com/i)).toBeTruthy();
  });
});
