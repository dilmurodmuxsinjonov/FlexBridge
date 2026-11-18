import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { GraduationCap } from "lucide-react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PasskeysPanel from "./PasskeysPanel";
import ContactsPanel from "./ContactsPanel";
import LoginPanel, { type LoginPanelConfig } from "../auth/LoginPanel";
import PasswordRecovery from "../auth/PasswordRecovery";

const navMock = vi.hoisted(() => ({ replace: vi.fn(), refresh: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navMock.replace, refresh: navMock.refresh, push: navMock.replace }),
  useSearchParams: () => navMock.params,
}));

const PK_ID = "11111111-1111-4111-8111-111111111111";
const CHALL_1 = "22222222-2222-4222-8222-222222222222";
const CHALL_2 = "33333333-3333-4333-8333-333333333333";

const portalConfig: LoginPanelConfig = {
  portal: "CANDIDATE",
  tone: "sky",
  icon: GraduationCap,
  badge: "Talaba",
  audience: "talaba",
  title: "Kirish",
  subtitle: "Sinov",
  identifierPlaceholder: "ali@otm.uz",
  submitLabel: "Kirish",
  home: "/nomzod",
  redirectPrefixes: ["/nomzod"],
  register: { href: "/talaba/royxatdan-otish", label: "Ro‘yxatdan o‘tish" },
  asideTitle: "Talaba",
  asideText: "",
  features: [],
};

function stubWebAuthnCredentialMock(mode: "create" | "get") {
  const bytes = new Uint8Array([1, 2, 3, 4]).buffer;
  class FakePublicKeyCredential {
    id = "cred-id-1";
    rawId = bytes;
    type = "public-key";
    response =
      mode === "create"
        ? { clientDataJSON: bytes, attestationObject: bytes, getTransports: () => ["internal"] }
        : { clientDataJSON: bytes, authenticatorData: bytes, signature: bytes, userHandle: bytes };
    getClientExtensionResults() {
      return {};
    }
  }
  const fakeCred = new FakePublicKeyCredential();
  vi.stubGlobal("PublicKeyCredential", FakePublicKeyCredential);
  vi.stubGlobal("navigator", {
    credentials: {
      create: vi.fn().mockResolvedValue(fakeCred),
      get: vi.fn().mockResolvedValue(fakeCred),
    },
  });
}

describe("Phase D Passkeys, Secondary Contacts, and Challenge Resend UI", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    navMock.replace.mockReset();
    navMock.refresh.mockReset();
    navMock.params = new URLSearchParams();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("enrolls and revokes a passkey via WebAuthn + step-up confirmation", async () => {
    stubWebAuthnCredentialMock("create");
    const calls: Array<{ url: string; method: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      calls.push({ url, method });

      if (url === "/api/bff/me/security/passkeys/options") {
        return new Response(
          JSON.stringify({
            ok: true,
            ceremony_token: "c".repeat(40),
            public_key: { challenge: "AQIDBA", user: { id: "AQIDBA" }, excludeCredentials: [] },
            expires_in: 300,
          }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/me/security/passkeys/verify") {
        return new Response(
          JSON.stringify({ ok: true, credential_id: PK_ID, passkey_enabled: true, reauthentication_required: true }),
          { status: 201 }
        );
      }
      if (url === `/api/bff/me/security/passkeys/${PK_ID}` && method === "DELETE") {
        return new Response(JSON.stringify({ ok: true, status: "REVOKED", reauthentication_required: true }), {
          status: 200,
        });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onUpdated = vi.fn();
    render(
      <PasskeysPanel
        passkeys={[{ id: PK_ID, device_type: "multiDevice", backed_up: true, created_at: "2026-11-18T10:00:00Z" }]}
        totpEnabled={false}
        onUpdated={onUpdated}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Passkey qo‘shish/i }));
    fireEvent.change(screen.getByPlaceholderText(/••••••••••••/i), { target: { value: "Password123!" } });
    fireEvent.click(screen.getByRole("button", { name: /Qurilma bilan tasdiqlash/i }));

    await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1));
    expect(calls.some((c) => c.url === "/api/bff/me/security/passkeys/verify")).toBe(true);

    fireEvent.click(screen.getAllByRole("button", { name: /O‘chirish/i })[0]);
    fireEvent.change(screen.getByPlaceholderText(/••••••••••••/i), { target: { value: "Password123!" } });
    fireEvent.click(screen.getByRole("button", { name: /Passkeyni o‘chirish/i }));

    await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(2));
    expect(calls.some((c) => c.url === `/api/bff/me/security/passkeys/${PK_ID}` && c.method === "DELETE")).toBe(
      true
    );
  });

  it("lists verified contacts and binds a new secondary contact with challenge resend", async () => {
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });

      if (url === "/api/bff/me/contacts" && method === "GET") {
        return new Response(
          JSON.stringify({
            ok: true,
            items: [{ id: "cnt-1", channel: "PHONE", masked_destination: "+99890***1234", is_primary: true }],
          }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/auth/options") {
        return new Response(JSON.stringify({ ok: true, telegram_mode: "DISABLED" }), { status: 200 });
      }
      if (url === "/api/bff/auth/challenges") {
        return new Response(JSON.stringify({ ok: true, challenge_id: CHALL_1, resend_after: 0 }), { status: 202 });
      }
      if (url === `/api/bff/auth/challenges/${CHALL_1}/resend`) {
        return new Response(JSON.stringify({ ok: true, challenge_id: CHALL_2, resend_after: 60 }), { status: 202 });
      }
      if (url === `/api/bff/auth/challenges/${CHALL_2}/consume`) {
        return new Response(JSON.stringify({ ok: true, verification_token: "v".repeat(40) }), { status: 200 });
      }
      if (url === "/api/bff/me/contacts" && method === "POST") {
        return new Response(JSON.stringify({ ok: true, contact_id: "cnt-2", verified: true }), { status: 201 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ContactsPanel totpEnabled={false} />);

    await waitFor(() => expect(screen.getByText("+99890***1234")).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: /Qo‘shimcha aloqa qo‘shish/i }));
    fireEvent.change(screen.getByPlaceholderText(/\+998901234567/i), { target: { value: "second@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: /Kod yuborish/i }));

    await waitFor(() => expect(screen.getByPlaceholderText(/6 xonali kod/i)).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Kodni qayta yuborish/i }));
    await waitFor(() => expect(calls.some((c) => c.url === `/api/bff/auth/challenges/${CHALL_1}/resend`)).toBe(true));

    fireEvent.change(screen.getByPlaceholderText(/6 xonali kod/i), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: /Kodni tasdiqlash/i }));

    await waitFor(() => expect(screen.getByPlaceholderText(/Tasdiqlash uchun joriy parol/i)).toBeTruthy());
    fireEvent.change(screen.getByPlaceholderText(/Tasdiqlash uchun joriy parol/i), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Aloqani bog‘lash/i }));

    await waitFor(() => expect(screen.getByText(/Qo‘shimcha aloqa manzili tasdiqlandi/i)).toBeTruthy());
    expect(calls.some((c) => c.url === "/api/bff/me/contacts" && c.method === "POST")).toBe(true);
  });

  it("signs in directly via Passkey in LoginPanel", async () => {
    stubWebAuthnCredentialMock("get");
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/auth/me") return new Response("{}", { status: 401 });
      if (url === "/api/auth/passkeys/options") {
        return new Response(
          JSON.stringify({
            ok: true,
            ceremony_token: "l".repeat(40),
            public_key: { challenge: "AQIDBA", allowCredentials: [] },
            expires_in: 300,
          }),
          { status: 200 }
        );
      }
      if (url === "/api/auth/passkeys/verify") {
        return new Response(JSON.stringify({ ok: true, user_id: "u-1", roles: ["CANDIDATE"] }), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<LoginPanel config={portalConfig} />);
    fireEvent.click(screen.getByRole("button", { name: /Passkey bilan kirish/i }));

    await waitFor(() => expect(navMock.replace).toHaveBeenCalledWith("/nomzod"));
  });

  it("calls API-021 resend endpoint during password recovery", async () => {
    const calls: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      calls.push(url);
      if (url === "/api/bff/auth/options") {
        return new Response(JSON.stringify({ ok: true, telegram_mode: "DISABLED" }), { status: 200 });
      }
      if (url === "/api/bff/auth/challenges") {
        return new Response(
          JSON.stringify({ ok: true, challenge_id: CHALL_1, delivery_method: "SMS", expires_in: 300, resend_after: 0 }),
          { status: 202 }
        );
      }
      if (url === `/api/bff/auth/challenges/${CHALL_1}/resend`) {
        return new Response(
          JSON.stringify({ ok: true, challenge_id: CHALL_2, delivery_method: "SMS", expires_in: 300, resend_after: 60 }),
          { status: 202 }
        );
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PasswordRecovery />);
    fireEvent.change(screen.getByLabelText("Telefon raqam yoki elektron pochta"), {
      target: { value: "90 123 45 67" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Kod olish/i }));

    const resendBtn = await screen.findByRole("button", { name: /Kodni qayta yuborish/i });
    fireEvent.click(resendBtn);

    await waitFor(() => expect(calls).toContain(`/api/bff/auth/challenges/${CHALL_1}/resend`));
  });
});
