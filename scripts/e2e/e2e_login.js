// Phase 1: real UI login for each role on its own sign-in page, then land on the cabinet.
const { chromium } = require("playwright-core");
const fs = require("fs");
const { BASE, totp, Run } = require("./e2e_lib");

const [,, outDir, credsPath] = process.argv;
const creds = JSON.parse(fs.readFileSync(credsPath, "utf8"));
const ROLES = [
  ["CANDIDATE", "/talaba/kirish", "/nomzod"],
  ["EMPLOYER", "/korxona/kirish", "/employer"],
  ["ACADEMIC", "/universitet/kirish", "/university"],
  ["OPERATOR", "/operator/kirish", "/operator"],
];

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  for (const [role, loginPath, home] of ROLES) {
    const run = new Run(outDir, `login_${role}`);
    const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const page = await ctx.newPage();
    run.attach(page);
    const c = creds[role].login;
    await run.step(page, "kirish sahifasi ochiladi", async () => {
      await page.goto(BASE + loginPath, { waitUntil: "networkidle" });
      await page.locator("input").first().waitFor({ timeout: 15000 });
    });
    await run.step(page, "telefon + parol bilan kirish", async () => {
      const id = page.locator('input[type="tel"], input[name="identifier"], input[autocomplete="username"], input[type="text"]').first();
      await id.fill(c.phone);
      await page.locator('input[type="password"]').first().fill(c.password);
      await page.locator('button[type="submit"]').first().click();
      await page.waitForTimeout(2500);
      return page.url();
    });
    if (c.totp_secret) {
      await run.step(page, "2FA kodini kiritish", async () => {
        const otp = page.locator('input[autocomplete="one-time-code"], input[inputmode="numeric"], input[placeholder="000000"], input[maxlength="6"]').first();
        await otp.waitFor({ timeout: 10000 });
        await otp.fill(totp(c.totp_secret));
        const submit = page.locator('button[type="submit"]').first();
        if (await submit.isEnabled().catch(() => false)) await submit.click().catch(() => undefined);
        await page.waitForTimeout(3000);
        return page.url();
      });
    }
    await run.step(page, `kabinet (${home}) ochiladi`, async () => {
      if (!page.url().includes(home)) await page.goto(BASE + home, { waitUntil: "networkidle" });
      await page.waitForTimeout(2000);
      const body = await page.locator("body").innerText();
      if (/tizimga kiring|Kirish talab|kirish uchun/i.test(body.slice(0, 1500)) && !/Chiqish/.test(body)) throw new Error("kirilmagan holat ko‘rinyapti");
      await page.screenshot({ path: `${outDir}/home_${role}.png`, fullPage: true });
      return page.url();
    });
    // keep the authenticated cookies for later phases
    fs.writeFileSync(`${outDir}/state_${role}.json`, JSON.stringify(await ctx.storageState()));
    run.save();
    await ctx.close();
  }
  await browser.close();
})();
