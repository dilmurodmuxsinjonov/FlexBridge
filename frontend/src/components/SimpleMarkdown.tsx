import React from "react";

/** Inline **bold** only; everything else stays plain text (no HTML is ever injected). */
function inline(text: string, keyBase: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") && p.length > 4 ? (
      <strong key={`${keyBase}-${i}`} className="font-semibold text-[var(--fb-ink)]">
        {p.slice(2, -2)}
      </strong>
    ) : (
      <React.Fragment key={`${keyBase}-${i}`}>{p}</React.Fragment>
    )
  );
}

/**
 * Minimal, safe Markdown for CMS policy/help texts: headings (#, ##, ###),
 * ordered/unordered lists, paragraphs and **bold**. Built from React nodes, so
 * stored content can never inject markup.
 */
export default function SimpleMarkdown({ source, skipFirstHeading = false }: { source: string; skipFirstHeading?: boolean }) {
  const lines = (source || "").replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let para: string[] = [];
  let headingSeen = false;

  const flushPara = () => {
    if (para.length) {
      const k = `p${blocks.length}`;
      blocks.push(
        <p key={k} className="leading-relaxed">
          {inline(para.join(" "), k)}
        </p>
      );
      para = [];
    }
  };
  const flushList = () => {
    if (list) {
      const k = `l${blocks.length}`;
      const items = list.items.map((it, i) => <li key={`${k}-${i}`}>{inline(it, `${k}-${i}`)}</li>);
      blocks.push(
        list.ordered ? (
          <ol key={k} className="list-decimal pl-5 space-y-1.5 leading-relaxed">
            {items}
          </ol>
        ) : (
          <ul key={k} className="list-disc pl-5 space-y-1.5 leading-relaxed">
            {items}
          </ul>
        )
      );
      list = null;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    const ol = line.match(/^\d+[.)]\s+(.*)$/);
    const ul = line.match(/^[-*•]\s+(.*)$/);
    if (!line) {
      flushPara();
      flushList();
    } else if (h) {
      flushPara();
      flushList();
      if (skipFirstHeading && !headingSeen) {
        headingSeen = true;
        continue;
      }
      headingSeen = true;
      const k = `h${blocks.length}`;
      const cls = "font-heading font-bold text-[var(--fb-ink)]";
      blocks.push(
        h[1].length === 1 ? (
          <h3 key={k} className={`${cls} text-lg`}>{h[2]}</h3>
        ) : (
          <h4 key={k} className={`${cls} text-base`}>{h[2]}</h4>
        )
      );
    } else if (ol || ul) {
      flushPara();
      const ordered = Boolean(ol);
      if (!list || list.ordered !== ordered) {
        flushList();
        list = { ordered, items: [] };
      }
      list.items.push((ol ? ol[1] : ul![1]) as string);
    } else {
      flushList();
      para.push(line);
    }
  }
  flushPara();
  flushList();

  return <div className="flex flex-col gap-3 text-sm sm:text-[15px] text-[var(--fb-ink-secondary)]">{blocks}</div>;
}
