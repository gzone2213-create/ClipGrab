/* =====================================================
   ClipGrab frontend logic (vanilla JS, no jQuery)
   Works both on the local Flask test page and on Blogger —
   just make sure API_BASE_URL is defined before this file loads.
   ===================================================== */

(function () {
  "use strict";

  const form = document.getElementById("searchForm");
  const urlInput = document.getElementById("videoUrl");
  const pasteBtn = document.getElementById("pasteBtn");
  const downloadBtn = document.getElementById("downloadBtn");
  const statusMsg = document.getElementById("statusMsg");
  const resultSection = document.getElementById("resultSection");
  const themeToggle = document.getElementById("themeToggle");

  const thumbImg = document.getElementById("thumbImg");
  const platformBadge = document.getElementById("platformBadge");
  const videoTitle = document.getElementById("videoTitle");
  const videoUploader = document.getElementById("videoUploader");
  const videoDuration = document.getElementById("videoDuration");
  const videoFormats = document.getElementById("videoFormats");
  const audioFormat = document.getElementById("audioFormat");

  let currentSourceUrl = "";

  /* ---------------- Theme (dark default, toggle to light) ---------------- */
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const icon = themeToggle.querySelector("i");
    icon.className = theme === "light" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
    localStorage.setItem("clipgrab-theme", theme);
  }

  (function initTheme() {
    const saved = localStorage.getItem("clipgrab-theme");
    const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
    applyTheme(saved || (prefersLight ? "light" : "dark"));
  })();

  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "light" ? "dark" : "light");
  });

  /* ---------------- Paste button ---------------- */
  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      urlInput.value = text.trim();
      urlInput.focus();
    } catch {
      showStatus("Couldn't read clipboard — paste manually with Ctrl+V.", "error");
    }
  });

  /* ---------------- Helpers ---------------- */
  function showStatus(message, kind) {
    statusMsg.textContent = message;
    statusMsg.className = "status-msg" + (kind ? " " + kind : "");
  }

  function setLoading(isLoading) {
    downloadBtn.disabled = isLoading;
    downloadBtn.querySelector(".btn-label").classList.toggle("d-none", isLoading);
    downloadBtn.querySelector(".btn-spinner").classList.toggle("d-none", !isLoading);
  }

  function isLikelyUrl(value) {
    try {
      const parsed = new URL(value);
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch {
      return false;
    }
  }

  /* ---------------- Main search flow ---------------- */
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();

    if (!url || !isLikelyUrl(url)) {
      showStatus("That doesn't look like a valid URL.", "error");
      return;
    }

    showStatus("");
    resultSection.classList.add("d-none");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/info`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();

      if (!res.ok) {
        showStatus(data.error || "Something went wrong. Try another link.", "error");
        return;
      }

      currentSourceUrl = url;
      renderResult(data);
      showStatus("Ready — pick a quality below.", "success");
    } catch (err) {
      showStatus("Couldn't reach the server. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  });

  function renderResult(data) {
    thumbImg.src = data.thumbnail || "";
    thumbImg.alt = data.title || "Video thumbnail";
    platformBadge.textContent = data.platform || "Video";
    videoTitle.textContent = data.title || "Untitled";
    videoUploader.textContent = data.uploader || "Unknown";
    videoDuration.textContent = data.duration || "N/A";

    videoFormats.innerHTML = "";
    if (data.formats && data.formats.length) {
      data.formats.forEach((fmt) => videoFormats.appendChild(buildFormatPill(fmt, false)));
    } else {
      videoFormats.innerHTML = '<p class="no-formats">No video formats were reported for this link.</p>';
    }

    audioFormat.innerHTML = "";
    if (data.audio) {
      audioFormat.appendChild(buildFormatPill(data.audio, true));
    } else {
      audioFormat.innerHTML = '<p class="no-formats">No separate audio stream available.</p>';
    }

    resultSection.classList.remove("d-none");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function buildFormatPill(fmt, isAudio) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "format-pill";

    const label = isAudio ? "MP3" : fmt.quality;
    const icon = isAudio ? "bi-file-earmark-music" : "bi-download";

    btn.innerHTML = `
      <i class="bi ${icon}"></i>
      <span>${label}</span>
      <span class="size">${fmt.filesize || ""}</span>
    `;

    btn.addEventListener("click", () => handleDownloadClick(btn, fmt.format_id, isAudio));
    return btn;
  }

  async function handleDownloadClick(btn, formatId, isAudio) {
    const original = btn.innerHTML;
    btn.classList.add("loading");
    btn.disabled = true;
    btn.innerHTML = `<i class="bi bi-arrow-repeat spin"></i> <span>Preparing…</span>`;

    try {
      const res = await fetch(`${API_BASE_URL}/api/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: currentSourceUrl, format_id: formatId }),
      });
      const data = await res.json();

      if (!res.ok || !data.download_url) {
        showStatus(data.error || "Couldn't prepare that download. Try another quality.", "error");
        return;
      }

      // Open the resolved direct link in a new tab so the browser
      // handles the actual file download/streaming.
      window.open(data.download_url, "_blank", "noopener");
      showStatus(isAudio ? "Audio download started." : "Download started.", "success");
    } catch (err) {
      showStatus("Network error while preparing the download.", "error");
    } finally {
      btn.classList.remove("loading");
      btn.disabled = false;
      btn.innerHTML = original;
    }
  }
})();
