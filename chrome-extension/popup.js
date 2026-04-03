// KB Clipper — popup.js

const PERSONAL_DOMAINS = [
  "technology/ai-ml", "technology/software-engineering", "technology/tools-productivity",
  "technology/hardware", "science/biology", "science/physics", "science/research-methods",
  "finance/investing", "finance/personal-finance", "finance/economics",
  "health/fitness", "health/nutrition", "health/mental-health",
  "career/leadership", "career/skills", "creativity/writing", "creativity/design",
  "learning/courses", "learning/books", "misc/ideas", "misc/reference"
];

const WORK_DOMAINS = [
  "projects/active", "projects/completed", "clients/accounts", "clients/research",
  "strategy/planning", "strategy/competitive", "processes/workflows", "processes/documentation",
  "people/team", "people/stakeholders", "meetings/notes", "meetings/decisions",
  "research/industry", "research/technical", "finance/budgets", "finance/reporting",
  "misc/reference", "misc/templates"
];

// ─── State ────────────────────────────────────────────────────────────────────

let state = {
  kb: "personal",
  mode: "article",
  saveMode: "native",   // "native" | "download"
  nativeConnected: false,
};

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  // Load saved settings
  const saved = await chrome.storage.local.get(["kb", "mode", "saveMode", "personalPath", "workPath", "recentDomains"]);
  if (saved.kb)       state.kb = saved.kb;
  if (saved.mode)     state.mode = saved.mode;
  if (saved.saveMode) state.saveMode = saved.saveMode;

  // Apply state to UI
  setActive("kbToggle", state.kb);
  setActive("modeToggle", state.mode);

  // Load page title
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.title) {
    document.getElementById("titleInput").value = tab.title;
  }

  // Populate domain suggestions
  updateDomainSuggestions(state.kb);
  populateRecentDomains(saved.recentDomains || []);

  // Check native host
  await checkNativeHost();

  // Settings panel
  document.getElementById("extensionId").textContent = chrome.runtime.id;
  document.getElementById("saveModeSelect").value = state.saveMode;
  if (saved.personalPath) document.getElementById("personalPathInput").value = saved.personalPath;
  if (saved.workPath)     document.getElementById("workPathInput").value = saved.workPath;
  toggleDownloadPathSection(state.saveMode);

  // Wire events
  wireEvents();
});

// ─── Event Wiring ─────────────────────────────────────────────────────────────

function wireEvents() {
  // KB toggle
  document.getElementById("kbToggle").addEventListener("click", (e) => {
    const btn = e.target.closest(".toggle-btn");
    if (!btn) return;
    state.kb = btn.dataset.value;
    setActive("kbToggle", state.kb);
    updateDomainSuggestions(state.kb);
    chrome.storage.local.set({ kb: state.kb });
  });

  // Mode toggle
  document.getElementById("modeToggle").addEventListener("click", (e) => {
    const btn = e.target.closest(".toggle-btn");
    if (!btn) return;
    state.mode = btn.dataset.value;
    setActive("modeToggle", state.mode);
    chrome.storage.local.set({ mode: state.mode });
  });

  // Auto-detect domain button
  document.getElementById("detectDomainBtn").addEventListener("click", autoDetectDomain);

  // Clip button
  document.getElementById("clipBtn").addEventListener("click", handleClip);

  // Settings link
  document.getElementById("settingsLink").addEventListener("click", (e) => {
    e.preventDefault();
    showSettings(true);
  });

  // Back button
  document.getElementById("backBtn").addEventListener("click", () => showSettings(false));

  // Save mode select
  document.getElementById("saveModeSelect").addEventListener("change", (e) => {
    toggleDownloadPathSection(e.target.value);
  });

  // Save settings button
  document.getElementById("saveSettingsBtn").addEventListener("click", saveSettings);

  // Domain chip click
  document.getElementById("domainChips").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) {
      document.getElementById("domainInput").value = chip.dataset.domain;
    }
  });
}

// ─── Core: Clip ───────────────────────────────────────────────────────────────

async function handleClip() {
  const btn = document.getElementById("clipBtn");
  const title = document.getElementById("titleInput").value.trim();
  const domain = document.getElementById("domainInput").value.trim() || "auto-detect";
  const tags = document.getElementById("tagsInput").value.trim();

  if (!title) {
    setStatus("Please enter a title", "error");
    return;
  }

  btn.disabled = true;
  setStatus("Extracting page content...", "info");

  try {
    // Inject content extractor
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractPageContent,
      args: [state.mode],
    });

    const { markdown, wordCount, imageCount } = results[0].result;

    if (!markdown || markdown.length < 50) {
      setStatus("Could not extract page content", "error");
      btn.disabled = false;
      return;
    }

    // Build the final markdown document
    const now = new Date().toISOString();
    const slug = slugify(title);
    const filename = `${slug}.md`;
    const content = buildMarkdownDocument({ title, markdown, domain, tags, url: tab.url, now });

    setStatus(`Saving ${wordCount} words...`, "info");

    if (state.saveMode === "native") {
      await saveViaNative({ filename, content, kb: state.kb, domain });
    } else {
      await saveViaDownload({ filename, content, kb: state.kb });
    }

    // Save recent domain
    await saveRecentDomain(domain);

    btn.classList.add("success");
    setStatus(`✓ Saved to ${state.kb}/raw/ (${wordCount} words, ${imageCount} images)`, "success");

    setTimeout(() => {
      btn.classList.remove("success");
      btn.disabled = false;
      setStatus("", "");
    }, 3000);

  } catch (err) {
    console.error(err);
    setStatus(`Error: ${err.message}`, "error");
    btn.disabled = false;
  }
}

// ─── Content Extractor (injected into page) ───────────────────────────────────

// NOTE: This function is serialized and injected into the page context.
// It cannot reference any variables from popup.js scope.
function extractPageContent(mode) {
  function getMainContent(mode) {
    if (mode === "selection") {
      const sel = window.getSelection();
      if (sel && sel.rangeCount > 0) {
        const div = document.createElement("div");
        for (let i = 0; i < sel.rangeCount; i++) {
          div.appendChild(sel.getRangeAt(i).cloneContents());
        }
        return div;
      }
    }
    if (mode === "full") return document.body;

    // Article mode: find main content
    const selectors = [
      "article", "[role='main']", "main", ".article-content", ".post-content",
      ".entry-content", ".content", "#content", ".markdown-body", ".prose"
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.innerText.length > 200) return el;
    }
    return document.body;
  }

  function cleanNode(node) {
    const unwanted = ["script", "style", "nav", "header", "footer", "aside",
      ".nav", ".navigation", ".sidebar", ".ad", ".advertisement", ".cookie-banner",
      ".popup", ".modal", ".share-buttons", ".social", ".related", ".comments"];
    const clone = node.cloneNode(true);
    unwanted.forEach(sel => {
      try { clone.querySelectorAll(sel).forEach(el => el.remove()); } catch(e) {}
    });
    return clone;
  }

  function nodeToMarkdown(node, depth) {
    if (!node) return "";
    depth = depth || 0;

    if (node.nodeType === 3) { // TEXT_NODE
      return node.textContent.replace(/\n{3,}/g, "\n\n");
    }
    if (node.nodeType !== 1) return ""; // ELEMENT_NODE

    const tag = node.tagName.toLowerCase();
    const childMd = () => Array.from(node.childNodes).map(c => nodeToMarkdown(c, depth)).join("");

    // Skip invisible elements
    const style = window.getComputedStyle(node);
    if (style.display === "none" || style.visibility === "hidden") return "";

    switch (tag) {
      case "h1": return `\n\n# ${childMd().trim()}\n\n`;
      case "h2": return `\n\n## ${childMd().trim()}\n\n`;
      case "h3": return `\n\n### ${childMd().trim()}\n\n`;
      case "h4": return `\n\n#### ${childMd().trim()}\n\n`;
      case "h5": return `\n\n##### ${childMd().trim()}\n\n`;
      case "h6": return `\n\n###### ${childMd().trim()}\n\n`;
      case "p":  return `\n\n${childMd().trim()}\n\n`;
      case "br": return "\n";
      case "hr": return "\n\n---\n\n";
      case "strong": case "b": {
        const inner = childMd().trim();
        return inner ? `**${inner}**` : "";
      }
      case "em": case "i": {
        const inner = childMd().trim();
        return inner ? `*${inner}*` : "";
      }
      case "s": case "del": {
        const inner = childMd().trim();
        return inner ? `~~${inner}~~` : "";
      }
      case "a": {
        const href = node.getAttribute("href") || "";
        const text = childMd().trim();
        if (!href || href.startsWith("javascript:") || !text) return text;
        const absHref = href.startsWith("http") ? href : new URL(href, window.location.href).href;
        return `[${text}](${absHref})`;
      }
      case "img": {
        const src = node.getAttribute("src") || "";
        const alt = node.getAttribute("alt") || "";
        if (!src || src.startsWith("data:")) return "";
        const absSrc = src.startsWith("http") ? src : new URL(src, window.location.href).href;
        return `![${alt}](${absSrc})`;
      }
      case "code": {
        if (node.parentElement?.tagName.toLowerCase() === "pre") return node.textContent;
        return `\`${node.textContent}\``;
      }
      case "pre": {
        const codeEl = node.querySelector("code");
        const lang = codeEl?.className?.match(/language-(\w+)/)?.[1] || "";
        const content = (codeEl || node).textContent;
        return `\n\n\`\`\`${lang}\n${content.trim()}\n\`\`\`\n\n`;
      }
      case "blockquote": {
        const inner = childMd().trim().split("\n").map(l => `> ${l}`).join("\n");
        return `\n\n${inner}\n\n`;
      }
      case "ul": {
        const items = Array.from(node.children)
          .filter(el => el.tagName.toLowerCase() === "li")
          .map(li => {
            const nested = li.querySelector("ul, ol");
            const text = nested
              ? Array.from(li.childNodes).filter(n => n !== nested).map(n => nodeToMarkdown(n, depth)).join("").trim()
              : nodeToMarkdown(li, depth).trim();
            const nestedMd = nested ? "\n" + nodeToMarkdown(nested, depth + 1).replace(/^/gm, "  ") : "";
            return `- ${text}${nestedMd}`;
          });
        return `\n\n${items.join("\n")}\n\n`;
      }
      case "ol": {
        let idx = 1;
        const items = Array.from(node.children)
          .filter(el => el.tagName.toLowerCase() === "li")
          .map(li => `${idx++}. ${nodeToMarkdown(li, depth).trim()}`);
        return `\n\n${items.join("\n")}\n\n`;
      }
      case "li": return childMd();
      case "table": {
        const rows = Array.from(node.querySelectorAll("tr"));
        if (!rows.length) return "";
        const tableLines = rows.map((row, i) => {
          const cells = Array.from(row.querySelectorAll("th, td"))
            .map(cell => cell.textContent.trim().replace(/\|/g, "\\|"));
          const line = `| ${cells.join(" | ")} |`;
          if (i === 0) {
            const sep = `| ${cells.map(() => "---").join(" | ")} |`;
            return `${line}\n${sep}`;
          }
          return line;
        });
        return `\n\n${tableLines.join("\n")}\n\n`;
      }
      case "div": case "section": case "article": case "main":
      case "figure": case "figcaption": case "span":
        return childMd();
      case "script": case "style": case "nav": case "header":
      case "footer": case "aside": case "button": case "form":
        return "";
      default:
        return childMd();
    }
  }

  const rawContent = getMainContent(mode);
  const cleaned = cleanNode(rawContent);
  let markdown = nodeToMarkdown(cleaned, 0);

  // Cleanup whitespace
  markdown = markdown
    .replace(/\n{4,}/g, "\n\n\n")
    .replace(/[ \t]+$/gm, "")
    .trim();

  const wordCount = markdown.split(/\s+/).filter(Boolean).length;
  const imageCount = (markdown.match(/!\[/g) || []).length;

  return { markdown, wordCount, imageCount };
}

// ─── Build Markdown Document ──────────────────────────────────────────────────

function buildMarkdownDocument({ title, markdown, domain, tags, url, now }) {
  const tagList = tags ? tags.split(",").map(t => t.trim()).filter(Boolean) : [];
  const frontmatter = [
    "---",
    `title: "${title}"`,
    `source_url: "${url}"`,
    `domain: "${domain}"`,
    `tags: [${tagList.map(t => `"${t}"`).join(", ")}]`,
    `date_ingested: "${now}"`,
    `compiled: false`,
    "---",
    "",
  ].join("\n");
  return frontmatter + markdown;
}

// ─── Save Methods ─────────────────────────────────────────────────────────────

async function saveViaNative({ filename, content, kb, domain }) {
  const response = await chrome.runtime.sendMessage({
    action: "saveToKB",
    payload: { filename, content, kb, domain },
  });

  if (!response?.success) {
    throw new Error(response?.error || "Native host failed");
  }
}

async function saveViaDownload({ filename, content, kb }) {
  const blob = new Blob([content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);

  await chrome.downloads.download({
    url,
    filename: `KB-${kb}-${filename}`,
    saveAs: false,
    conflictAction: "uniquify",
  });
}

// ─── Native Host Check ────────────────────────────────────────────────────────

async function checkNativeHost() {
  const dot = document.getElementById("statusDot");
  const hostStatus = document.getElementById("hostStatus");

  try {
    const response = await chrome.runtime.sendMessage({ action: "ping" });
    if (response?.pong) {
      state.nativeConnected = true;
      dot.className = "status-dot connected";
      hostStatus.textContent = `Native host connected`;
      if (response.personalPath || response.workPath) {
        hostStatus.textContent = `Connected · ${response.personalPath?.split("/").slice(-3, -1).join("/")}`;
      }
    } else {
      throw new Error("no pong");
    }
  } catch {
    state.nativeConnected = false;
    const saved = await chrome.storage.local.get("saveMode");
    if (saved.saveMode === "download") {
      dot.className = "status-dot download-mode";
      hostStatus.textContent = "Download mode (native not connected)";
    } else {
      dot.className = "status-dot disconnected";
      hostStatus.textContent = "Native host not found — see Settings";
    }
  }
}

// ─── Auto-detect Domain ───────────────────────────────────────────────────────

async function autoDetectDomain() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = new URL(tab.url);
  const hostname = url.hostname.replace("www.", "");
  const title = document.getElementById("titleInput").value.toLowerCase();
  const domains = state.kb === "personal" ? PERSONAL_DOMAINS : WORK_DOMAINS;

  // Simple URL-based heuristics
  const rules = {
    "arxiv.org": "science/research-methods",
    "github.com": "technology/software-engineering",
    "medium.com": "misc/reference",
    "substack.com": "misc/reference",
    "openai.com": "technology/ai-ml",
    "anthropic.com": "technology/ai-ml",
    "huggingface.co": "technology/ai-ml",
    "paperswithcode.com": "technology/ai-ml",
    "nature.com": "science/research-methods",
    "pubmed.ncbi.nlm.nih.gov": "health/misc",
    "investopedia.com": "finance/investing",
    "stripe.com": "technology/tools-productivity",
    "notion.so": "technology/tools-productivity",
  };

  const suggested = rules[hostname];
  if (suggested && domains.includes(suggested)) {
    document.getElementById("domainInput").value = suggested;
    setStatus(`Suggested: ${suggested}`, "info");
    setTimeout(() => setStatus("", ""), 2000);
    return;
  }

  // Keyword matching on title
  const keywords = {
    "ai": "technology/ai-ml", "machine learning": "technology/ai-ml",
    "llm": "technology/ai-ml", "gpt": "technology/ai-ml", "neural": "technology/ai-ml",
    "invest": "finance/investing", "stock": "finance/investing", "fund": "finance/investing",
    "health": "health/fitness", "workout": "health/fitness", "nutrition": "health/nutrition",
    "coding": "technology/software-engineering", "programming": "technology/software-engineering",
    "python": "technology/software-engineering", "javascript": "technology/software-engineering",
    "book": "learning/books", "course": "learning/courses",
    "leadership": "career/leadership", "management": "career/leadership",
    "design": "creativity/design", "writing": "creativity/writing",
  };

  for (const [kw, domain] of Object.entries(keywords)) {
    if (title.includes(kw)) {
      document.getElementById("domainInput").value = domain;
      setStatus(`Suggested: ${domain}`, "info");
      setTimeout(() => setStatus("", ""), 2000);
      return;
    }
  }

  setStatus("Could not auto-detect — please enter manually", "info");
  setTimeout(() => setStatus("", ""), 2500);
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────

function setActive(groupId, value) {
  const group = document.getElementById(groupId);
  group.querySelectorAll(".toggle-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.value === value);
  });
}

function setStatus(msg, type) {
  const el = document.getElementById("statusMsg");
  el.textContent = msg;
  el.className = `status-msg${type ? " " + type : ""}`;
}

function updateDomainSuggestions(kb) {
  const domains = kb === "personal" ? PERSONAL_DOMAINS : WORK_DOMAINS;
  const datalist = document.getElementById("domainSuggestions");
  datalist.innerHTML = domains.map(d => `<option value="${d}">`).join("");
}

async function populateRecentDomains(recent) {
  const chips = document.getElementById("domainChips");
  const toShow = recent.slice(0, 4);
  chips.innerHTML = toShow.map(d =>
    `<span class="chip" data-domain="${d}">${d}</span>`
  ).join("");
}

async function saveRecentDomain(domain) {
  if (!domain || domain === "auto-detect") return;
  const { recentDomains = [] } = await chrome.storage.local.get("recentDomains");
  const updated = [domain, ...recentDomains.filter(d => d !== domain)].slice(0, 8);
  await chrome.storage.local.set({ recentDomains: updated });
  populateRecentDomains(updated);
}

function slugify(title) {
  return title.toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 60)
    .replace(/^-+|-+$/g, "");
}

function showSettings(show) {
  document.querySelector(".container").style.display = show ? "none" : "flex";
  document.getElementById("settingsPanel").style.display = show ? "flex" : "none";
}

function toggleDownloadPathSection(mode) {
  document.getElementById("downloadPathSection").style.display =
    mode === "download" ? "flex" : "none";
}

async function saveSettings() {
  const saveMode = document.getElementById("saveModeSelect").value;
  const personalPath = document.getElementById("personalPathInput").value.trim();
  const workPath = document.getElementById("workPathInput").value.trim();

  state.saveMode = saveMode;
  await chrome.storage.local.set({ saveMode, personalPath, workPath });

  setStatus("Settings saved", "success");
  setTimeout(() => {
    setStatus("", "");
    showSettings(false);
    checkNativeHost();
  }, 1000);
}
