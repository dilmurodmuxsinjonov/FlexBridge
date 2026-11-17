// Shared helpers for the staging browser E2E run (real accounts, no mocks).
const crypto = require("crypto");
const fs = require("fs");

const BASE = process.env.E2E_BASE || "http://127.0.0.1:3000";

function totp(secret, at = Date.now()) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const clean = secret.replace(/=+$/, "").replace(/\s+/g, "").toUpperCase();
  let bits = "";
  for (const c of clean) bits += alphabet.indexOf(c).toString(2).padStart(5, "0");
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  const key = Buffer.from(bytes);
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(at / 1000 / 30)));
  const h = crypto.createHmac("sha1", key).update(counter).digest();
  const o = h[h.length - 1] & 0xf;
  const code = ((h.readUInt32BE(o) & 0x7fffffff) % 1_000_000).toString().padStart(6, "0");
  return code;
}

class Run {
  constructor(outDir, role) {
    this.outDir = outDir;
    this.role = role;
    this.results = [];
    this.netErrors = [];
    this.pageErrors = [];
  }

  attach(page) {
    page.on("pageerror", (e) => this.pageErrors.push({ step: this.current, msg: e.message.slice(0, 200) }));
    page.on("response", (r) => {
      const u = r.url();
      if (u.includes("/api/") && r.status() >= 400) {
        this.netErrors.push({ step: this.current, status: r.status(), method: r.request().method(), path: new URL(u).pathname });
      }
    });
  }

  async step(page, name, fn) {
    this.current = name;
    const t0 = Date.now();
    try {
      const note = await fn();
      this.results.push({ name, ok: true, ms: Date.now() - t0, note: note || "" });
      console.log(`  PASS ${this.role} | ${name}${note ? " — " + note : ""}`);
    } catch (e) {
      const shot = `${this.outDir}/${this.role}_${this.results.length}_fail.png`;
      await page.screenshot({ path: shot, fullPage: true }).catch(() => undefined);
      this.results.push({ name, ok: false, ms: Date.now() - t0, note: String(e.message || e).split("\n")[0].slice(0, 220), shot });
      console.log(`  FAIL ${this.role} | ${name} — ${String(e.message || e).split("\n")[0].slice(0, 220)}`);
    }
  }

  save() {
    fs.writeFileSync(`${this.outDir}/${this.role}_report.json`, JSON.stringify({ role: this.role, results: this.results, netErrors: this.netErrors, pageErrors: this.pageErrors }, null, 1));
  }
}

module.exports = { BASE, totp, Run };
