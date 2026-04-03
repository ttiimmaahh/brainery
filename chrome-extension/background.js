// KB Clipper — background.js (Service Worker)
// Communicates with the Brainery clip server via HTTP (localhost:52337)

const SERVER_URL = "http://127.0.0.1:52337";

// ─── Message Router ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "ping") {
    handlePing(sendResponse);
    return true; // keep channel open for async response
  }

  if (message.action === "saveToKB") {
    handleSave(message.payload, sendResponse);
    return true;
  }
});

// ─── Ping (health check) ──────────────────────────────────────────────────────

async function handlePing(sendResponse) {
  try {
    const resp = await fetch(`${SERVER_URL}/api/ping`);
    const data = await resp.json();
    sendResponse({
      pong: true,
      personalPath: data.personalPath,
      workPath: data.workPath,
      version: data.version,
    });
  } catch (err) {
    sendResponse({ pong: false, error: err.message });
  }
}

// ─── Save ─────────────────────────────────────────────────────────────────────

async function handleSave(payload, sendResponse) {
  try {
    const resp = await fetch(`${SERVER_URL}/api/clip`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: payload.filename,
        content: payload.content,
        kb: payload.kb,
        domain: payload.domain,
      }),
    });

    const data = await resp.json();

    if (data.success) {
      sendResponse({ success: true, path: data.path });
    } else {
      sendResponse({ success: false, error: data.error || "Unknown error from server" });
    }
  } catch (err) {
    sendResponse({ success: false, error: err.message });
  }
}

// ─── Keyboard Shortcut ────────────────────────────────────────────────────────

chrome.commands?.onCommand?.addListener(async (command) => {
  if (command === "quick-clip") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;

    // Quick clip: use stored settings, no popup
    const stored = await chrome.storage.local.get(["kb", "recentDomains", "saveMode"]);
    const kb = stored.kb || "personal";
    const domain = (stored.recentDomains || [])[0] || "misc/reference";

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: quickExtract,
    });

    if (!results?.[0]?.result) return;

    const { markdown, title } = results[0].result;
    const now = new Date().toISOString();
    const slug = title.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").slice(0, 60);
    const filename = `${slug}.md`;
    const content = buildQuickDoc({ title, markdown, domain, url: tab.url, now });

    if (stored.saveMode === "download") {
      const blob = new Blob([content], { type: "text/markdown" });
      const blobUrl = URL.createObjectURL(blob);
      await chrome.downloads.download({
        url: blobUrl,
        filename: `KB-${kb}-${filename}`,
        saveAs: false,
        conflictAction: "uniquify",
      });
    } else {
      try {
        await fetch(`${SERVER_URL}/api/clip`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename, content, kb, domain }),
        });
      } catch (err) {
        console.error("KB Clipper: clip server not reachable", err);
      }
    }

    // Brief notification
    chrome.notifications?.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "KB Clipper",
      message: `Saved "${title.slice(0, 50)}" to ${kb} KB`,
    });
  }
});

// Quick extract (injected into page, no UI)
function quickExtract() {
  const title = document.title;
  const article = document.querySelector("article, [role='main'], main") || document.body;
  const clone = article.cloneNode(true);
  ["script","style","nav","header","footer","aside"].forEach(tag => {
    clone.querySelectorAll(tag).forEach(el => el.remove());
  });
  return { title, markdown: clone.innerText.slice(0, 15000) };
}

function buildQuickDoc({ title, markdown, domain, url, now }) {
  return `---\ntitle: "${title}"\nsource_url: "${url}"\ndomain: "${domain}"\ndate_ingested: "${now}"\ncompiled: false\n---\n\n${markdown}`;
}
