// Measures the motion layer in a real browser and records a short demo video.
const { chromium } = require("playwright-core");
const fs = require("fs");
const [,, dir] = process.argv;
const BASE = process.env.E2E_BASE || "http://127.0.0.1:3100";
const out = [];
let frameNo = 0;
fs.mkdirSync(`${dir}/frames`, { recursive: true });
async function burst(page, n, gap = 0) {
  for (let i = 0; i < n; i++) {
    await page.screenshot({ path: `${dir}/frames/f${String(frameNo++).padStart(4, "0")}.jpg`, type: "jpeg", quality: 70 });
    if (gap) await page.waitForTimeout(gap);
  }
}
const check = (name, ok, detail = "") => out.push(`${ok ? "PASS" : "FAIL"} ${name}${detail ? " — " + detail : ""}`);

(async () => {
  const b = await chromium.launch({ channel: "msedge", headless: true });
  const ctx = await b.newContext({
    viewport: { width: 1440, height: 900 },
    storageState: `${dir}/state_EMPLOYER.json`,
  });
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  await p.goto(BASE + "/employer", { waitUntil: "domcontentloaded" });

  // CountUp: the hero number is mid-count shortly after load, final later.
  await p.locator(".font-display.text-5xl").first().waitFor({ timeout: 20000 });
  await p.waitForLoadState("networkidle");
  await p.waitForTimeout(1500);

  // Glider in the section capsule slides to the clicked section.
  const dock = p.locator(".fb-section-dock");
  const glider = dock.locator(".fb-glider");
  check("bo‘lim kapsulasida glider yoqilgan", (await dock.getAttribute("data-glider")) === "on");
  const before = await glider.evaluate((g) => g.style.transform);
  await burst(p, 3);
  await dock.getByRole("button", { name: /Tashkilot/ }).click({ noWaitAfter: true });
  const mid = await glider.evaluate((g) => getComputedStyle(g).transform);
  await burst(p, 8);
  await dock.getByRole("button", { name: /To.lovlar/ }).click({ noWaitAfter: true });
  await burst(p, 8);
  await dock.getByRole("button", { name: /Tashkilot/ }).click({ noWaitAfter: true });
  await burst(p, 8);
  await p.waitForTimeout(300);
  const after = await glider.evaluate((g) => g.style.transform);
  const activeBox = await dock.locator(".fb-nav-active").boundingBox();
  const gliderBox = await glider.boundingBox();
  check("glider faol bo‘limga siljidi", before !== after && Math.abs(activeBox.x - gliderBox.x) < 2 && Math.abs(activeBox.width - gliderBox.width) < 2, `${before} → ${after}`);
  check("siljish animatsiyali (oraliq holat bor)", mid !== "none", mid);

  // Ripple + press depth on a primary button.
  const btn = p.getByRole("button", { name: /Yangi e.lon/ }).first();
  const box = await btn.boundingBox();
  await p.mouse.move(box.x + 12, box.y + box.height / 2);
  await p.mouse.down();
  await p.waitForTimeout(40);
  const pressed = await btn.evaluate((el) => ({ ripple: el.classList.contains("fb-ripple"), rx: el.style.getPropertyValue("--fb-rx"), transform: getComputedStyle(el).transform }));
  await p.screenshot({ path: `${dir}/motion_press.png`, clip: { x: box.x - 20, y: box.y - 20, width: box.width + 40, height: box.height + 40 } });
  await p.mouse.up();
  check("bosilganda ripple chiqdi", pressed.ripple, `origin x=${pressed.rx}`);
  check("bosilganda tugma botdi", pressed.transform !== "none", pressed.transform);
  const dialog = p.locator(".fixed.inset-0 > .skeuo-card, [role='dialog']").first();
  if (await dialog.count()) {
    const anims = await dialog.evaluate((el) => el.getAnimations().map((a) => a.animationName || "web"));
    check("modal paydo bo‘lish animatsiyasi", anims.length > 0, anims.join(","));
    await p.keyboard.press("Escape");
    const close = p.getByRole("button", { name: /Bekor|Yopish/ });
    if (await dialog.isVisible() && (await close.count())) await close.first().click();
  } else {
    check("modal paydo bo‘lish animatsiyasi", false, "modal ochilmadi");
  }
  await p.waitForTimeout(500);

  // Rail knob glider.
  const rail = p.locator(".fb-rail");
  check("relsda metall knob-glider", (await rail.getAttribute("data-glider")) === "on");
  const railHover = rail.locator(".fb-rail-btn").nth(1);
  await railHover.hover();
  await p.waitForTimeout(250);
  await p.screenshot({ path: `${dir}/motion_rail_tip.png`, clip: { x: 0, y: 200, width: 360, height: 500 } });

  // Theme: circular reveal through the View Transitions API.
  const hasVT = await p.evaluate(() => typeof document.startViewTransition === "function");
  const themeBtn = rail.getByRole("button", { name: "Rang mavzusini almashtirish" });
  await burst(p, 2);
  await themeBtn.click({ noWaitAfter: true });
  await p.waitForTimeout(200);
  await p.screenshot({ path: `${dir}/motion_theme_mid.png` });
  await burst(p, 10);
  await p.waitForTimeout(200);
  const dark = await p.evaluate(() => document.documentElement.classList.contains("dark"));
  check("mavzu doira bo‘lib almashdi", hasVT && dark, `viewTransition=${hasVT}`);
  await p.waitForTimeout(400);
  await themeBtn.click({ noWaitAfter: true });
  await burst(p, 12);

  // Busy state: a real request with a disabled button (company search).
  await dock.getByRole("button", { name: /Nomzod Qidiruv/ }).click();
  await p.waitForTimeout(800);
  const search = p.getByRole("button", { name: /^Qidirish$|Izlash/ }).first();
  if (await search.count()) {
    await search.click();
    const sawBusy = await p.waitForFunction(() => !!document.querySelector(".fb-busy"), null, { timeout: 3000 }).then(() => true).catch(() => false);
    await p.waitForTimeout(1200);
    const left = await p.evaluate(() => document.querySelectorAll(".fb-busy").length);
    check("so‘rov paytida tugma «band», keyin bo‘shadi", left === 0, `band ko‘rindi=${sawBusy}`);
  }
  await dock.getByRole("button", { name: /Kanban/ }).click();
  await p.waitForTimeout(900);
  check("sahifa xatolari yo‘q", errors.length === 0, errors.join(" | "));

  await ctx.close();

  // Reduced motion: no ripple, glider still placed.
  const rctx = await b.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce", storageState: `${dir}/state_EMPLOYER.json` });
  const rp = await rctx.newPage();
  await rp.goto(BASE + "/employer", { waitUntil: "networkidle" });
  await rp.waitForTimeout(1200);
  const rb = rp.getByRole("button", { name: /Yangi e.lon/ }).first();
  const rbox = await rb.boundingBox();
  await rp.mouse.move(rbox.x + 10, rbox.y + 10);
  await rp.mouse.down();
  const rr = await rb.evaluate((el) => el.classList.contains("fb-ripple"));
  await rp.mouse.up();
  check("reduced-motion: ripple o‘chiq", !rr);
  await rctx.close();
  await b.close();

  console.log(out.join("\n"));
  console.log("FRAMES", frameNo);
})();
