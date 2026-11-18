// Full cross-role run against the rebuilt staging (current integration UI).
const { chromium } = require("playwright-core");
const { BASE, Run } = require("./e2e_lib");

const [,, outDir] = process.argv;
const TAG = `E2E ${Date.now().toString(36).slice(-5)}`;
const VACANCY = `${TAG} QA amaliyotchi`;

async function act(page, click, { match = null, timeout = 20000, allow = [] } = {}) {
  const resp = page
    .waitForResponse((r) => r.url().includes("/api/") && r.request().method() !== "GET" && (!match || match.test(new URL(r.url()).pathname)), { timeout })
    .catch((e) => e);
  await click();
  const r = await resp;
  if (r instanceof Error) throw new Error("backend'ga so‘rov ketmadi (tugma ishlamadi yoki forma tekshiruvi)");
  let code = "";
  try {
    const j = await r.json();
    act.last = j;
    code = typeof j.error === "string" ? j.error : j.detail?.code || "";
  } catch {}
  const line = `${r.status()} ${r.request().method()} ${new URL(r.url()).pathname}${code ? " " + code : ""}`;
  if (r.status() >= 400 && !allow.includes(code)) throw new Error(line);
  return line;
}

const open = async (browser, role) => {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, storageState: `${outDir}/state_${role}.json` });
  return { ctx, page: await ctx.newPage() };
};

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const E = new Run(outDir, "v2_EMPLOYER");
  const O = new Run(outDir, "v2_OPERATOR");
  const C = new Run(outDir, "v2_CANDIDATE");
  const U = new Run(outDir, "v2_ACADEMIC");
  const emp = await open(browser, "EMPLOYER");
  const op = await open(browser, "OPERATOR");
  const cand = await open(browser, "CANDIDATE");
  const uni = await open(browser, "ACADEMIC");
  E.attach(emp.page); O.attach(op.page); C.attach(cand.page); U.attach(uni.page);
  const ep = emp.page, opp = op.page, cp = cand.page, up = uni.page;

  // ---- EMPLOYER creates a vacancy ----
  await E.step(ep, "korxona paneli ochiladi", async () => {
    await ep.goto(BASE + "/employer", { waitUntil: "networkidle" });
    await ep.getByRole("heading", { level: 1, name: "Korxona paneli" }).waitFor({ timeout: 20000 });
    await ep.screenshot({ path: `${outDir}/v2_employer_home.png`, fullPage: true });
  });
  await E.step(ep, "e’lon yaratish", async () => {
    await ep.getByRole("button", { name: /Yangi e.lon/ }).first().click();
    await ep.locator("#create-title").fill(VACANCY);
    await ep.locator("#create-kind").selectOption("GENERAL_INTERNSHIP").catch(() => undefined);
    const line = await act(ep, () => ep.getByRole("button", { name: /E.lonni yaratish/ }).click());
    const ok = ep.getByRole("button", { name: /Tushunarli|Yopish/ });
    if (await ok.count()) await ok.first().click().catch(() => undefined);
    return line;
  });
  await E.step(ep, "e’lon ro‘yxatda «Moderatsiyada»", async () => {
    await ep.reload({ waitUntil: "networkidle" });
    await ep.waitForTimeout(1500);
    const t = await ep.locator("body").innerText();
    if (!t.includes(VACANCY)) throw new Error("yangi e’lon ro‘yxatda yo‘q");
    return /Moderatsiyada/.test(t) ? "Moderatsiyada" : "holat yozuvi topilmadi";
  });

  // ---- OPERATOR approves it ----
  await O.step(opp, "operator: e’lonlar moderatsiyasi", async () => {
    await opp.goto(BASE + "/operator", { waitUntil: "networkidle" });
    await opp.getByRole("button", { name: /E.lonlar moderatsiyasi/ }).first().click();
    await opp.getByText(VACANCY).first().waitFor({ timeout: 15000 });
    return "e’lon navbatda";
  });
  await O.step(opp, "operator: e’lonni tasdiqlash", async () => {
    const item = opp.locator("li").filter({ hasText: VACANCY }).first();
    await item.getByRole("button", { name: /^Tasdiqlash$/ }).click();
    await item.getByLabel(/Izoh/).fill("E2E: matn, to‘lov va shartnoma turi tekshirildi");
    return act(opp, () => item.getByRole("button", { name: "Tasdiqlashni yuborish" }).click(), { match: /moderation/ });
  });

  // ---- EMPLOYER publishes (plan may be required) ----
  await E.step(ep, "e’lonni nashr qilish", async () => {
    await ep.reload({ waitUntil: "networkidle" });
    await ep.waitForTimeout(1500);
    const sel = ep.locator("#kanbanOppPicker");
    const v = await sel.locator("option", { hasText: VACANCY }).first().getAttribute("value");
    await sel.selectOption(v);
    global.OPP = v;
    return act(ep, () => ep.getByRole("button", { name: /Nashr qilish/ }).first().click(), { allow: ["ACTIVE_ENTITLEMENT_REQUIRED"] });
  });
  await E.step(ep, "tarif sahifasi (to‘lovlar)", async () => {
    await ep.getByRole("button", { name: /To.lovlar/ }).first().click();
    await ep.waitForTimeout(2000);
    await ep.screenshot({ path: `${outDir}/v2_employer_billing.png`, fullPage: true });
    const buy = ep.getByRole("button", { name: /Tarifini Olish|Sotib olish|Buyurtma berish/ }).first();
    if (!(await buy.count())) return "tarif tugmasi yo‘q (skrinshot)";
    return act(ep, () => buy.click(), { allow: ["PAYMENT_GATEWAY_UNAVAILABLE", "PAYMENT_PROVIDER_UNAVAILABLE"] });
  });

  // ---- CANDIDATE ----
  await C.step(cp, "talaba profili ochiladi", async () => {
    await cp.goto(BASE + "/nomzod", { waitUntil: "networkidle" });
    await cp.getByRole("heading", { level: 1 }).first().waitFor({ timeout: 20000 });
    await cp.screenshot({ path: `${outDir}/v2_candidate_home.png`, fullPage: true });
  });
  for (const [path, heading] of [["/nomzod/jadval", /O.quv jadvali/], ["/nomzod/kundalik", /Kundalik/], ["/xabarlar", /Xabarlar/]]) {
    await C.step(cp, `sahifa ${path}`, async () => {
      await cp.goto(BASE + path, { waitUntil: "networkidle" });
      await cp.getByRole("heading", { level: 1, name: heading }).waitFor({ timeout: 20000 });
      await cp.screenshot({ path: `${outDir}/v2_candidate_${path.replace(/\W+/g, "_")}.png`, fullPage: true });
    });
  }
  await C.step(cp, "katalogdan e’lon ochib ariza topshirish", async () => {
    await cp.goto(BASE + "/elonlar", { waitUntil: "networkidle" });
    await cp.waitForTimeout(1500);
    const mine = cp.getByText(VACANCY);
    if (await mine.count()) await mine.first().click();
    else await cp.getByRole("link", { name: /Batafsil|Ko.rish/ }).first().click();
    await cp.waitForURL(/\/ishlar\//, { timeout: 15000 });
    await cp.waitForTimeout(1200);
    global.JOB = (await cp.locator("h1").first().innerText()).trim();
    await cp.getByRole("button", { name: /Ariza topshirish/ }).first().click();
    await cp.waitForTimeout(800);
    for (const box of await cp.locator('input[type="checkbox"]').all()) if (await box.isVisible()) await box.check().catch(() => undefined);
    return act(cp, () => cp.getByRole("button", { name: /Arizani jo.natish|Yuborish/ }).last().click(), { match: /apply|applications/, allow: ["ALREADY_APPLIED", "DUPLICATE_APPLICATION"] }).then((l) => `${global.JOB}: ${l}`);
  });

  // ---- CHAT: employer shares code, candidate writes, employer replies ----
  await E.step(ep, "chat: korxona kontakt kodini oladi", async () => {
    await ep.goto(BASE + "/xabarlar", { waitUntil: "networkidle" });
    await ep.getByRole("button", { name: /Yangi suhbat$/ }).click();
    const dlg = ep.getByRole("dialog", { name: "Yangi suhbat" });
    await dlg.getByText(/^[A-Z0-9]{8}$/).first().waitFor({ timeout: 15000 });
    global.CODE = (await dlg.getByText(/^[A-Z0-9]{8}$/).first().innerText()).trim();
    await ep.keyboard.press("Escape");
    return global.CODE;
  });
  await C.step(cp, "chat: talaba kod orqali yozadi", async () => {
    await cp.goto(BASE + "/xabarlar", { waitUntil: "networkidle" });
    await cp.getByRole("button", { name: /Yangi suhbat$/ }).click();
    const dlg = cp.getByRole("dialog", { name: "Yangi suhbat" });
    await dlg.getByLabel("Kontakt kod orqali").fill(global.CODE);
    await act(cp, () => dlg.getByRole("button", { name: "Yozish" }).click(), { match: /chat\/direct/ });
    await cp.getByLabel("Xabar", { exact: true }).fill(`${TAG}: Assalomu alaykum! Ariza bo‘yicha savolim bor.`);
    return act(cp, () => cp.getByLabel("Xabar", { exact: true }).press("Enter"), { match: /messages/ });
  });
  await E.step(ep, "chat: korxona xabarni ko‘rib javob beradi", async () => {
    await ep.goto(BASE + "/xabarlar", { waitUntil: "networkidle" });
    await ep.waitForTimeout(1500);
    await ep.getByRole("button", { name: /Audit Talaba/ }).first().click();
    await ep.getByText(`${TAG}: Assalomu alaykum!`, { exact: false }).first().waitFor({ timeout: 15000 });
    await ep.getByLabel("Xabar", { exact: true }).fill("Vaalaykum assalom! Savolingizni yozing.");
    const line = await act(ep, () => ep.getByLabel("Xabar", { exact: true }).press("Enter"), { match: /messages/ });
    await ep.screenshot({ path: `${outDir}/v2_chat_employer.png` });
    return line;
  });
  await C.step(cp, "chat: talaba javobni ko‘radi", async () => {
    await cp.waitForTimeout(5000);
    await cp.getByText("Vaalaykum assalom!").first().waitFor({ timeout: 15000 });
    await cp.screenshot({ path: `${outDir}/v2_chat_candidate.png` });
    return "javob keldi";
  });
  await C.step(cp, "chat: guruh ochish", async () => {
    await cp.getByRole("button", { name: /Yangi suhbat$/ }).click();
    const dlg = cp.getByRole("dialog", { name: "Yangi suhbat" });
    await dlg.getByRole("button", { name: "Guruh" }).click();
    await dlg.getByLabel("Guruh nomi").fill(`${TAG} guruhi`);
    const contact = dlg.locator("li button").first();
    if (await contact.count()) await contact.click();
    return act(cp, () => dlg.getByRole("button", { name: "Guruh yaratish" }).click(), { match: /chat\/groups/ });
  });

  // ---- EMPLOYER sees the application in the kanban ----
  await E.step(ep, "kanbanda arizalarni yuklash", async () => {
    await ep.goto(BASE + "/employer", { waitUntil: "networkidle" });
    await ep.waitForTimeout(1500);
    const sel = ep.locator("#kanbanOppPicker");
    const has = await sel.locator("option", { hasText: VACANCY }).count();
    if (!has) throw new Error("e’lon tanlovda yo‘q");
    await sel.selectOption(global.OPP);
    await act(ep, () => ep.getByRole("button", { name: /Nomzodlarni yuklash/ }).first().click()).catch(() => undefined);
    await ep.waitForTimeout(2500);
    await ep.screenshot({ path: `${outDir}/v2_kanban.png`, fullPage: true });
    const t = await ep.locator("body").innerText();
    return /Frontend|E2E|Nomzod/.test(t) ? "kanban yuklandi" : "kanban bo‘sh";
  });

  // ---- UNIVERSITY ----
  await U.step(up, "akademik panel ochiladi", async () => {
    await up.goto(BASE + "/university", { waitUntil: "networkidle" });
    await up.getByRole("heading", { level: 1, name: "Akademik panel" }).waitFor({ timeout: 20000 });
    await up.screenshot({ path: `${outDir}/v2_university_home.png`, fullPage: true });
  });
  await U.step(up, "dars jadvaliga dars qo‘shish", async () => {
    await up.getByRole("button", { name: /Dars Jadvali/ }).first().click();
    await up.waitForTimeout(1800);
    await up.getByPlaceholder(/Sun.iy intellekt|Fan nomi/i).first().fill(`${TAG} Algoritmlar`);
    return act(up, () => up.getByRole("button", { name: /Darsni Jadvalga Qo.shish/i }).first().click(), { match: /timetable/ });
  });
  await U.step(up, "yig‘ma hisobot yaratish", async () => {
    await up.getByRole("button", { name: /Yig.ma Hisobotlar/ }).first().click();
    await up.waitForTimeout(1500);
    return act(up, () => up.getByRole("button", { name: /Hisobotni Shakllantirish/i }).first().click(), { match: /export/, timeout: 40000 });
  });
  await U.step(up, "xodimlar va talabalik bo‘limlari", async () => {
    for (const tab of [/Xodimlar/, /Talabalikni tasdiqlash/, /Analitika/]) {
      await up.getByRole("button", { name: tab }).first().click();
      await up.waitForTimeout(1500);
    }
    return "ochildi";
  });

  // ---- OPERATOR overview ----
  await O.step(opp, "operator paneli umumiy ko‘rinish", async () => {
    await opp.goto(BASE + "/operator", { waitUntil: "networkidle" });
    await opp.getByRole("heading", { level: 1, name: "Operator paneli" }).waitFor({ timeout: 20000 });
    await opp.screenshot({ path: `${outDir}/v2_operator_home.png`, fullPage: true });
  });

  for (const r of [E, O, C, U]) r.save();
  await browser.close();
  console.log("TAG", TAG);
})();
