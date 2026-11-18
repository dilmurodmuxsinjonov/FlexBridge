// Screenshots of the device-shell design on every window, light/dark, desktop/phone.
const { chromium } = require("playwright-core");
const [,, dir] = process.argv;
const BASE = process.env.E2E_BASE || "http://127.0.0.1:3100";
const PAGES = [
  ["GUEST", "/", "home"], ["GUEST", "/elonlar", "elonlar"], ["GUEST", "/kirish", "login"],
  ["CANDIDATE", "/nomzod", "cand"], ["CANDIDATE", "/nomzod/jadval", "cand_jadval"], ["CANDIDATE", "/xabarlar", "chat"],
  ["EMPLOYER", "/employer", "emp"], ["ACADEMIC", "/university", "uni"], ["OPERATOR", "/operator", "op"],
];
(async () => {
  const b = await chromium.launch({ channel: "msedge", headless: true });
  const report = [];
  for (const [role, path, name] of PAGES) {
    for (const [mode, vp] of [["desk", { width: 1440, height: 900 }], ["phone", { width: 390, height: 844 }]]) {
      for (const theme of mode === "desk" ? ["light", "dark"] : ["light"]) {
        const ctx = await b.newContext({ viewport: vp, colorScheme: theme, ...(role === "GUEST" ? {} : { storageState: `${dir}/state_${role}.json` }) });
        const p = await ctx.newPage();
        const errs = [];
        p.on("pageerror", (e) => errs.push(e.message));
        await p.addInitScript((t) => { try { localStorage.setItem("flexbridge:theme", t); } catch {} }, theme);
        await p.goto(BASE + path, { waitUntil: "networkidle" });
        await p.waitForTimeout(1500);
        const info = await p.evaluate(() => {
          const dock = document.querySelector(".fb-section-dock");
          const main = document.querySelector(".fb-main-dock");
          const rail = document.querySelector(".fb-rail");
          const vis = (el) => !!el && getComputedStyle(el).display !== "none" && el.getBoundingClientRect().width > 0;
          return {
            dark: document.documentElement.classList.contains("dark"),
            sectionDock: vis(dock) ? dock.querySelectorAll(".fb-nav-item").length : 0,
            mainDock: vis(main), rail: vis(rail),
            hScroll: document.documentElement.scrollWidth > window.innerWidth + 1,
          };
        });
        const file = `${dir}/shell_${name}_${mode}_${theme}.png`;
        await p.screenshot({ path: file });
        report.push({ name, mode, theme, ...info, errors: errs.length });
        await ctx.close();
      }
    }
  }
  console.log(JSON.stringify(report, null, 0).replace(/\},\{/g, "},\n{"));
  await b.close();
})();
