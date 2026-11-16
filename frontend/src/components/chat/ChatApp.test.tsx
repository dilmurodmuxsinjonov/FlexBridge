import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchConversations: vi.fn(),
  fetchConversation: vi.fn(),
  fetchMessages: vi.fn(),
  sendMessage: vi.fn(),
  markRead: vi.fn(),
  deleteMessage: vi.fn(),
  joinByToken: vi.fn(),
  fetchContacts: vi.fn(),
  fetchMyContactCode: vi.fn(),
  rotateContactCode: vi.fn(),
  startDirect: vi.fn(),
  createGroup: vi.fn(),
  renameGroup: vi.fn(),
  addGroupMembers: vi.fn(),
  removeGroupMember: vi.fn(),
  enableInviteLink: vi.fn(),
  disableInviteLink: vi.fn(),
  setBlocked: vi.fn(),
}));
vi.mock("@/lib/chat", async (orig) => ({ ...(await orig<typeof import("@/lib/chat")>()), ...api }));

import ChatApp from "./ChatApp";
import { chatTime, inviteUrl } from "@/lib/chat";

const ME = "11111111-1111-4111-8111-111111111111";
const conv = (over = {}) => ({
  id: "c1",
  kind: "DIRECT",
  title: "Aziz Rahimov",
  partner_id: "p1",
  member_count: 2,
  my_role: "MEMBER",
  unread_count: 2,
  last_message: { body: "Salom!", deleted: false, sender_id: "p1", sender_name: "Aziz Rahimov", mine: false, created_at: new Date().toISOString() },
  updated_at: new Date().toISOString(),
  ...over,
});

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  api.fetchConversations.mockResolvedValue({ items: [conv(), conv({ id: "g1", kind: "GROUP", title: "Amaliyot jamoasi", partner_id: null, member_count: 5, unread_count: 0, last_message: null })], unread_total: 2 });
  api.fetchConversation.mockImplementation(async (id: string) => ({ ...conv({ id }), members: [], invite_link_active: null, blocked: false }));
  api.fetchMessages.mockResolvedValue({
    items: [
      { id: "m1", sender_id: "p1", sender_name: "Aziz Rahimov", body: "Salom!", deleted: false, mine: false, created_at: new Date().toISOString() },
      { id: "m2", sender_id: ME, sender_name: "Men", body: null, deleted: true, mine: true, created_at: new Date().toISOString() },
    ],
    has_more: false,
  });
  api.markRead.mockResolvedValue({ ok: true });
  api.sendMessage.mockResolvedValue({ id: "m3" });
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});
afterEach(() => vi.useRealTimers());

describe("chat helpers", () => {
  it("formats times relative to today and builds invite URLs", () => {
    const now = new Date(2026, 10, 16, 18, 0);
    expect(chatTime(new Date(2026, 10, 16, 9, 5).toISOString(), now)).toBe("09:05");
    expect(chatTime(new Date(2026, 10, 15, 23, 0).toISOString(), now)).toBe("Kecha");
    expect(chatTime(new Date(2026, 10, 2, 8, 0).toISOString(), now)).toBe("02.11");
    expect(inviteUrl("abc/def", "https://fb.uz")).toBe("https://fb.uz/xabarlar?qoshilish=abc%2Fdef");
  });
});

describe("ChatApp", () => {
  it("lists conversations with previews and unread badges", async () => {
    render(<ChatApp meId={ME} />);
    const list = await screen.findByRole("region", { name: "Suhbatlar" });
    expect(within(list).getByText("Aziz Rahimov")).toBeInTheDocument();
    expect(within(list).getByLabelText("2 ta o‘qilmagan")).toBeInTheDocument();
    expect(within(list).getByText("5 a’zo")).toBeInTheDocument();
  });

  it("opens a thread, marks it read, hides deleted text and sends with Enter", async () => {
    render(<ChatApp meId={ME} />);
    fireEvent.click(await screen.findByRole("button", { name: /Aziz Rahimov/ }));
    const thread = await screen.findByRole("region", { name: "Suhbat: Aziz Rahimov" });
    expect(await within(thread).findByText("Xabar o‘chirildi")).toBeInTheDocument();
    await waitFor(() => expect(api.markRead).toHaveBeenCalledWith("c1"));

    const box = within(thread).getByLabelText("Xabar");
    fireEvent.change(box, { target: { value: "  Ertaga 10:00 da  " } });
    fireEvent.keyDown(box, { key: "Enter" });
    await waitFor(() => expect(api.sendMessage).toHaveBeenCalledWith("c1", "Ertaga 10:00 da"));
    await waitFor(() => expect(box).toHaveValue(""));
  });

  it("joins a group from an invite token and opens it", async () => {
    const joined = { ...conv({ id: "g9", kind: "GROUP", title: "Yangi guruh" }), members: [], invite_link_active: null, blocked: false };
    api.joinByToken.mockResolvedValue(joined);
    api.fetchConversation.mockResolvedValue(joined);
    const onJoinHandled = vi.fn();
    render(<ChatApp meId={ME} joinToken="tok_1234567890abcdef" onJoinHandled={onJoinHandled} />);
    await waitFor(() => expect(api.joinByToken).toHaveBeenCalledWith("tok_1234567890abcdef"));
    await waitFor(() => expect(onJoinHandled).toHaveBeenCalled());
    expect(await screen.findByRole("region", { name: "Suhbat: Yangi guruh" })).toBeInTheDocument();
  });

  it("shows a readable error when the invite link is no longer valid", async () => {
    api.joinByToken.mockRejectedValue(new Error("Taklif havolasi yaroqsiz yoki o‘chirilgan."));
    render(<ChatApp meId={ME} joinToken="tok_1234567890abcdef" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Taklif havolasi yaroqsiz");
  });

  it("starts a direct chat by contact code from the new-chat dialog", async () => {
    api.fetchContacts.mockResolvedValue([]);
    api.fetchMyContactCode.mockResolvedValue({ contact_code: "ABCD2345" });
    const started = { ...conv({ id: "c7", title: "Laylo" }), members: [], invite_link_active: null, blocked: false };
    api.startDirect.mockResolvedValue(started);
    api.fetchConversation.mockResolvedValue(started);
    render(<ChatApp meId={ME} />);
    fireEvent.click(screen.getByRole("button", { name: /Yangi suhbat$/ }));
    const dialog = await screen.findByRole("dialog", { name: "Yangi suhbat" });
    expect(await within(dialog).findByText("ABCD2345")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Kontakt kod orqali"), { target: { value: "wxyz-6789" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Yozish" }));
    await waitFor(() => expect(api.startDirect).toHaveBeenCalledWith({ contact_code: "WXYZ6789" }));
    expect(await screen.findByRole("region", { name: "Suhbat: Laylo" })).toBeInTheDocument();
  });
});
