// AudioLibro Libre — interfaz del asistente de 5 pasos (JavaScript vanilla, sin build).
import { api, ApiError } from "./api.js";
import { t, setLang, currentLang, applyStatic, fmtDuration, fmtBytes } from "./i18n.js";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const RECOMMENDED = { es: "es_ES-davefx-medium", en: "en_US-joe-medium" };
const CHARS_PER_SECOND = 14.5;

const S = {
  job: null, step: 1, system: null, selKey: null, voices: [], settings: null,
  poll: null, lastStatus: null, tutorial: false, audio: null, keySeq: 0, voiceBusy: new Set(),
};

/* ------------------------------------------------------------- utilidades */
function el(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === false || v == null) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  kids.flat().forEach((c) => e.append(c?.nodeType ? c : document.createTextNode(c ?? "")));
  return e;
}

const announce = (msg) => { $("#live").textContent = ""; setTimeout(() => { $("#live").textContent = msg; }, 50); };

function showError(err) {
  const box = $("#error-box");
  if (!err) { box.hidden = true; box.replaceChildren(); return; }
  const code = err instanceof ApiError ? err.code : "unexpected";
  const known = t(`errors.${code}.msg`) !== `errors.${code}.msg`;
  const c = known ? code : "unexpected";
  const params = { ...(err.params || {}), detail: err.detail || err.message || "" };
  box.replaceChildren(
    el("h3", { text: t("common.error_title") }),
    el("p", { text: t(`errors.${c}.msg`, params) }),
    el("p", { class: "err-hint" }, el("strong", { text: t("common.what_to_do") + " " }), t(`errors.${c}.hint`, params)),
  );
  box.hidden = false;
  box.scrollIntoView({ block: "nearest" });
}

async function guard(fn) {
  try { return await fn(); } catch (e) { showError(e); return undefined; }
}

const busy = () => ["running", "queued"].includes(S.job?.state?.status);
const safeStorage = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento */ } },
};
const minutesOf = (chars) => Math.max(1, Math.round(chars / CHARS_PER_SECOND / 60));
const keyOf = (c) => c._k;

/* ------------------------------------------------------------ navegación */
function updateStepper() {
  $$("#stepper button").forEach((b) => {
    const n = Number(b.dataset.step);
    b.disabled = !S.job && n > 1;
    if (n === S.step) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
  });
}

function setHash() {
  const h = S.job ? `#job=${S.job.id}&step=${S.step}` : "";
  history.replaceState(null, "", location.pathname + h);
}

async function goStep(n) {
  showError(null);
  if (S.job && !busy()) {
    if (S.step === 2 && n !== 2 && !(await saveBook())) return;
    if (S.step === 3 && n !== 3 && !(await saveSettings())) return;
  }
  stopPolling();
  S.step = n;
  $$(".step").forEach((s) => { s.hidden = s.id !== `step-${n}`; });
  $$(".tutorial-tip").forEach((p) => {
    p.hidden = !S.tutorial;
    p.textContent = S.tutorial ? t(`tutorial.s${S.step}`) : "";
  });
  updateStepper();
  setHash();
  const enter = { 1: enterStep1, 2: enterStep2, 3: enterStep3, 4: enterStep4, 5: enterStep5 }[n];
  await guard(enter);
  $(`#h-${n}`).focus({ preventScroll: false });
  window.scrollTo({ top: 0 });
}

async function openJob(job, step) {
  S.job = prepareJob(job);
  S.settings = { ...S.job.settings, pronunciation: [...(S.job.settings.pronunciation || [])] };
  S.selKey = null;
  S.lastStatus = null;
  await goStep(step);
}

function prepareJob(job) {
  job.book.chapters.forEach((c) => { c._k = c.id != null ? `c${c.id}` : `n${++S.keySeq}`; });
  return job;
}

function stepForStatus(job) {
  const st = job.state.status;
  if (st === "done") return 5;
  if (["running", "queued", "paused", "cancelled", "error"].includes(st)) return 4;
  return 2;
}

/* ---------------------------------------------------------------- paso 1 */
const legalOk = () => $("#legal-accept").checked;

function applyLegalGate() {
  const ok = legalOk();
  $("#file").disabled = !ok;
  $('label[for="file"]').setAttribute("aria-disabled", String(!ok));
  $("#demo-es").disabled = !ok;
  $("#demo-en").disabled = !ok;
}

async function enterStep1() {
  $("#formats").textContent = t("s1.formats", { formats: (S.system?.supported_formats || [".txt", ".epub"]).join(" ") });
  $("#file").accept = (S.system?.supported_formats || [".txt", ".epub"]).join(",");
  const ocr = $("#ocr-note");
  ocr.hidden = !S.system || S.system.tesseract;
  $("#book-lang").value = currentLang();
  applyLegalGate();
  const list = await api.jobs();
  const ul = $("#project-list");
  ul.replaceChildren();
  $("#projects-empty").hidden = list.length > 0;
  list.forEach((p) => {
    ul.append(el("li", { class: "proj" },
      el("div", { class: "info" }, el("strong", { text: p.title }),
        el("span", { text: `${p.author ? p.author + " · " : ""}${t("s1.chapters_n", { n: p.chapters })} · ${t(`s1.status.${p.status}`)}` })),
      el("div", { class: "row" },
        el("button", { type: "button", class: "btn secondary", text: t("s1.open"), onclick: () => guard(async () => { const j = await api.job(p.id); await openJob(j, stepForStatus(j)); }) }),
        el("button", { type: "button", class: "btn danger", text: t("s1.delete"), onclick: () => guard(async () => {
          if (!confirm(t("s1.delete_confirm", { title: p.title }))) return;
          await api.deleteJob(p.id); await enterStep1();
        }) }))));
  });
}

async function handleFile(file) {
  if (!file) return;
  if (!legalOk()) return;
  showError(null);
  $("#upload-status").textContent = t("s1.reading");
  const token = Math.random().toString(36).slice(2, 12);
  const timer = setInterval(async () => {
    try {
      const p = await api.uploadProgress(token);
      if (p.total > 0) $("#upload-status").textContent = t(p.stage === "ocr" ? "s1.ocr_progress" : "s1.reading_pdf", { done: p.done, total: p.total });
    } catch { /* el progreso es solo informativo */ }
  }, 1000);
  try {
    const job = await api.upload(file, $("#book-lang").value, token);
    await openJob(job, 2);
  } catch (e) { showError(e); } finally { clearInterval(timer); $("#upload-status").textContent = ""; $("#file").value = ""; }
}

async function startDemo(lang) {
  await guard(async () => {
    const job = await api.demo(lang);
    await openJob(job, 2);
  });
}

/* ---------------------------------------------------------------- paso 2 */
function selChapter() { return S.job.book.chapters.find((c) => keyOf(c) === S.selKey); }

function enterStep2() {
  const b = S.job.book;
  $("#meta-title").value = b.title;
  $("#meta-author").value = b.author;
  $("#meta-lang").value = b.language;
  $("#skip-hint").hidden = !b.chapters.some((c) => !c.included);
  if (!selChapter()) S.selKey = b.chapters.length ? keyOf(b.chapters[0]) : null;
  renderChapters();
}

function renderChapters() {
  const chapters = S.job.book.chapters;
  const ul = $("#chapter-list");
  ul.replaceChildren();
  chapters.forEach((c) => {
    const chars = c.text.length;
    ul.append(el("li", { class: c.included ? "" : "off" },
      el("input", { type: "checkbox", checked: c.included, "aria-label": `${t("s2.include")}: ${c.title}`,
        onchange: (e) => { c.included = e.target.checked; renderChapters(); } }),
      el("button", { type: "button", class: "ch-btn", "aria-current": String(keyOf(c) === S.selKey),
        onclick: () => { S.selKey = keyOf(c); renderChapters(); } },
      c.title || "—", el("small", { text: t("s2.chars", { n: chars.toLocaleString(currentLang()), min: minutesOf(chars) }) }))));
  });
  const inc = chapters.filter((c) => c.included).length;
  $("#chapter-summary").textContent = inc ? t("s2.summary", { n: inc, total: chapters.length }) : t("s2.none_selected");
  $("#s2-next").disabled = inc === 0;
  const sel = selChapter();
  $("#editor-empty").hidden = !!sel;
  $("#editor-body").hidden = !sel;
  $("#chapter-del").disabled = chapters.length <= 1;
  if (sel) {
    if ($("#ch-title").dataset.key !== keyOf(sel)) {
      $("#ch-title").value = sel.title;
      $("#ch-text").value = sel.text;
      $("#ch-title").dataset.key = keyOf(sel);
    }
    $("#ch-count").textContent = t("s2.chars", { n: sel.text.length.toLocaleString(currentLang()), min: minutesOf(sel.text.length) });
  } else { $("#ch-title").dataset.key = ""; }
}

async function saveBook() {
  const b = S.job.book;
  if (!b.chapters.some((c) => c.included)) { showError(new ApiError("no_chapters_selected")); return false; }
  const payload = {
    title: b.title || "Libro", author: b.author, language: b.language,
    chapters: b.chapters.map((c) => ({ id: c.id ?? null, title: c.title, text: c.text, included: c.included })),
  };
  try {
    const job = await api.saveBook(S.job.id, payload);
    const selIdx = b.chapters.findIndex((c) => keyOf(c) === S.selKey);
    S.job = prepareJob(job);
    const list = S.job.book.chapters;
    S.selKey = list.length ? keyOf(list[Math.min(Math.max(0, selIdx), list.length - 1)]) : null;
    return true;
  } catch (e) { showError(e); return false; }
}

/* ---------------------------------------------------------------- paso 3 */
let saveTimer = null;
function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => guard(async () => { if (await saveSettings()) await renderEstimate(); }), 600);
}

function collectSettings() {
  const s = S.settings;
  s.speed = Number($("#speed").value);
  s.pause_paragraph = Number($("#pause-p").value || 0);
  s.pause_chapter = Number($("#pause-c").value || 0);
  s.read_titles = $("#read-titles").checked;
  s.speaker = Number($("#speaker").value || 0);
  s.pronunciation = $$(".pron-row").map((r) => ({
    source: $(".pron-from", r).value.trim(), spoken: $(".pron-to", r).value.trim(), whole_word: true, case_sensitive: true,
  })).filter((r) => r.source);
  return s;
}

async function saveSettings() {
  if (!S.job || busy()) return true;
  try {
    const job = await api.saveSettings(S.job.id, collectSettings());
    S.job.settings = job.settings;
    S.job.state = job.state;
    return true;
  } catch (e) { showError(e); return false; }
}

async function enterStep3() {
  const s = S.settings;
  $("#voice-lang").value = S.job.book.language;
  $("#speed").value = s.speed;
  $("#speed-out").textContent = Number(s.speed).toFixed(2).replace(/0$/, "");
  $("#pause-p").value = s.pause_paragraph;
  $("#pause-c").value = s.pause_chapter;
  $("#read-titles").checked = s.read_titles;
  $("#speaker").value = s.speaker;
  renderPron();
  await loadVoices();
  // La voz elegida por defecto debe guardarse antes de estimar (así se mide su velocidad real).
  if (S.settings.voice !== S.job.settings.voice) await saveSettings();
  await renderEstimate();
}

async function loadVoices() {
  S.voices = await api.voices($("#voice-lang").value);
  const rank = (v) => (v.id === RECOMMENDED[v.lang] ? 0 : 1);
  const qual = { medium: 0, high: 1, low: 2, x_low: 3 };
  S.voices.sort((a, b) => rank(a) - rank(b) || (qual[a.quality] ?? 9) - (qual[b.quality] ?? 9) || a.id.localeCompare(b.id));
  if (!S.settings.voice || !S.voices.some((v) => v.id === S.settings.voice)) {
    const inst = S.voices.find((v) => v.installed);
    S.settings.voice = (inst || S.voices[0])?.id || "";
  }
  renderVoices();
}

function renderVoices() {
  const wrap = $("#voice-list");
  wrap.replaceChildren();
  S.voices.forEach((v) => {
    const selected = v.id === S.settings.voice;
    const pid = `v-${v.id}`;
    const bar = el("progress", { max: "100", value: "0", hidden: true, "aria-label": t("s3.downloading", { pct: 0 }) });
    const card = el("div", { class: `voice${selected ? " selected" : ""}`, "data-voice": v.id },
      el("label", { class: "pick", for: pid },
        el("input", { type: "radio", name: "voice", id: pid, value: v.id, checked: selected, onchange: () => {
          S.settings.voice = v.id; S.settings.speaker = 0; $("#speaker").value = 0; renderVoices(); scheduleSave();
        } }),
        el("span", {}, `${v.name} (${v.locale.replace("_", "-")})`,
          v.id === RECOMMENDED[v.lang] ? el("span", { class: "badge", text: t("s3.recommended") }) : "",
          v.installed ? el("span", { class: "badge", text: t("s3.installed") }) : "")),
      el("p", { class: "meta", text: `${t("s3.quality", { q: t(`s3.quality.${v.quality}`) })} · ${fmtBytes(v.size_bytes)}${v.speakers > 1 ? " · " + t("s3.speakers", { n: v.speakers }) : ""}` }),
      el("p", { class: "meta fine", text: t("s3.license", { license: v.license }) + (v.attribution_required ? " — " + t("s3.attribution") : "") }),
      bar,
      el("div", { class: "row" },
        v.installed ? "" : el("button", { type: "button", class: "btn ghost", text: t("s3.download"), onclick: (e) => installVoice(v, card, e.target) }),
        el("button", { type: "button", class: "btn secondary", text: t("s3.sample"), onclick: (e) => playSample(v, card, e.target) })));
    wrap.append(card);
  });
  const cur = S.voices.find((v) => v.id === S.settings.voice);
  $("#speaker-field").hidden = !(cur && cur.speakers > 1);
  if (cur && cur.speakers > 1) $("#speaker").max = String(cur.speakers - 1);
}

async function installVoice(v, card, btn) {
  if (S.voiceBusy.has(v.id)) return true;
  S.voiceBusy.add(v.id);
  const bar = $("progress", card);
  if (btn) btn.disabled = true;
  bar.hidden = false;
  try {
    let st = await api.installVoice(v.id);
    while (st.state === "running") {
      const pct = st.total ? Math.round((100 * st.done) / st.total) : 0;
      bar.value = pct;
      bar.setAttribute("aria-label", t("s3.downloading", { pct }));
      $("#sample-status").textContent = t("s3.downloading", { pct });
      await new Promise((r) => setTimeout(r, 600));
      st = await api.installStatus(v.id);
    }
    if (st.state === "error") throw new ApiError(st.error.code, st.error.detail, st.error.params);
    v.installed = true;
    $("#sample-status").textContent = "";
    announce(`${v.name}: ${t("s3.installed")}`);
    renderVoices();
    return true;
  } catch (e) {
    showError(e);
    if (btn) btn.disabled = false;
    bar.hidden = true;
    return false;
  } finally { S.voiceBusy.delete(v.id); }
}

async function playSample(v, card, btn) {
  showError(null);
  if (!v.installed && !(await installVoice(v, card, null))) return;
  btn.disabled = true;
  $("#sample-status").textContent = t("s3.sample_loading");
  try {
    const blob = await api.sample(v.id, { speed: Number($("#speed").value), speaker: Number($("#speaker").value || 0) });
    if (S.audio) S.audio.pause();
    S.audio = new Audio(URL.createObjectURL(blob));
    await S.audio.play();
    $("#sample-status").textContent = "";
  } catch (e) { showError(e); $("#sample-status").textContent = ""; } finally { btn.disabled = false; }
}

function renderPron() {
  const wrap = $("#pron-list");
  wrap.replaceChildren();
  (S.settings.pronunciation || []).forEach((r, i) => {
    const a = `pf-${i}`, b = `pt-${i}`;
    wrap.append(el("div", { class: "pron-row" },
      el("div", {}, el("label", { for: a, text: t("s3.pron_from") }), el("input", { id: a, type: "text", class: "pron-from", value: r.source, maxlength: "100", oninput: scheduleSave })),
      el("div", {}, el("label", { for: b, text: t("s3.pron_to") }), el("input", { id: b, type: "text", class: "pron-to", value: r.spoken, maxlength: "200", oninput: scheduleSave })),
      el("button", { type: "button", class: "btn danger", text: t("s3.pron_remove"), onclick: () => {
        collectSettings(); S.settings.pronunciation.splice(i, 1); renderPron(); scheduleSave();
      } })));
  });
}

async function renderEstimate() {
  if (!S.job) return;
  const e = await api.estimate(S.job.id);
  const free = e.system.disk_free_bytes, ram = e.system.ram_total_bytes;
  const ul = $("#estimate");
  ul.replaceChildren(
    el("li", { text: t("s3.est_audio", { value: fmtDuration(e.audio_seconds) }) }),
    el("li", { text: t("s3.est_time", { value: fmtDuration(e.generation_seconds) }) + (e.rtf_measured ? "" : " " + t("s3.est_time_unmeasured")) }),
    el("li", { text: t("s3.est_disk", { value: fmtBytes(e.disk_bytes), free: fmtBytes(free) }) }),
    el("li", { text: t("s3.est_ram", { value: fmtBytes(e.ram_bytes), total: ram ? fmtBytes(ram) : "?" }) }),
  );
  if (e.disk_bytes * 1.2 > free) ul.append(el("li", { class: "notice error", text: t("s3.disk_warn") }));
  if (ram && e.ram_bytes > ram * 0.8) ul.append(el("li", { class: "notice warn", text: t("s3.ram_warn") }));
}

async function step3Next() {
  const v = S.voices.find((x) => x.id === S.settings.voice);
  if (!v) { showError(new ApiError("voice_not_selected")); return; }
  if (!v.installed) { showError(new ApiError("voice_not_installed")); return; }
  await goStep(4);
}

/* ---------------------------------------------------------------- paso 4 */
function stopPolling() { clearInterval(S.poll); S.poll = null; }

async function enterStep4() {
  await refreshProgress();
}

function startPolling() {
  if (S.poll) return;
  S.poll = setInterval(() => guard(refreshProgress), 1000);
}

async function refreshProgress() {
  const p = await api.progress(S.job.id);
  renderProgress(p);
  if (["running", "queued"].includes(p.status)) startPolling(); else stopPolling();
}

function renderProgress(p) {
  S.job.state.status = p.status;
  const st = p.status;
  $("#gen-state").textContent = t(`s4.state.${st}`);
  if (S.lastStatus !== st) { announce(t(`s4.state.${st}`)); S.lastStatus = st; }
  const running = ["running", "queued"].includes(st);
  const start = $("#gen-start");
  start.hidden = running || st === "done";
  start.textContent = p.done_chunks > 0 ? t("s4.resume") : t("s4.start");
  $("#gen-pause").hidden = !running;
  $("#gen-cancel").hidden = !running;
  const bar = $("#gen-bar");
  bar.value = p.percent;
  $("#gen-bar-label").textContent = t("s4.overall", { done: p.done_chunks, total: p.total_chunks, pct: p.percent });
  $("#gen-overall").textContent = t("s4.overall", { done: p.done_chunks, total: p.total_chunks, pct: p.percent });
  $("#gen-times").textContent = running
    ? [p.eta_seconds != null ? t("s4.eta", { value: fmtDuration(p.eta_seconds) }) : "", t("s4.elapsed", { value: fmtDuration(p.elapsed_seconds) })].filter(Boolean).join(" · ")
    : "";
  if (st === "error" && p.error) showError(new ApiError(p.error.code, p.error.detail, p.error.params));
  const ul = $("#gen-chapters");
  ul.replaceChildren();
  p.chapters.forEach((c) => {
    const pct = c.total ? Math.round((100 * c.done) / c.total) : 0;
    ul.append(el("li", { class: "gen-ch" },
      el("span", { text: c.title + (p.current_chapter === c.id ? " ▶" : "") }),
      el("progress", { max: "100", value: String(pct), "aria-label": `${c.title}: ${pct}%` }),
      el("span", { class: "hint", text: t("s4.chapter_row", { done: c.done, total: c.total }) }),
      el("button", { type: "button", class: "btn ghost", text: t("s4.listen"), disabled: c.done === 0,
        onclick: () => listen(c) })));
  });
  $("#s4-next").disabled = st !== "done";
}

async function listen(c) {
  showError(null);
  try {
    const blob = await api.preview(S.job.id, c.id);
    const a = $("#preview-audio");
    a.src = URL.createObjectURL(blob);
    a.hidden = false;
    $("#preview-title").textContent = t("s4.preview", { title: c.title });
    await a.play();
  } catch (e) { showError(e); }
}

async function generate(action) {
  showError(null);
  await guard(async () => {
    if (action === "start") await saveSettings();
    const p = action === "start" ? await api.start(S.job.id) : await api[action](S.job.id);
    if (action === "start") { renderProgress(p); startPolling(); } else { await new Promise((r) => setTimeout(r, 300)); await refreshProgress(); }
  });
}

/* ---------------------------------------------------------------- paso 5 */
async function enterStep5() {
  const b = S.job.book;
  $("#export-meta").textContent = t("s5.meta", { title: b.title, author: b.author || "—" });
  renderCover();
  $("#export-result").hidden = true;
  $("#export-bar").hidden = true;
  $("#export-status").textContent = "";
  const st = await api.exportStatus(S.job.id);
  if (st.state === "done") showExportDone(st);
  else if (st.state === "running") pollExport();
}

function renderCover() {
  const has = S.job.has_cover;
  const img = $("#cover-img");
  img.hidden = !has;
  $("#cover-none").hidden = has;
  if (has) { img.src = api.coverUrl(S.job.id); img.alt = t("s5.cover"); }
}

function showExportDone(st) {
  $("#export-bar").hidden = true;
  $("#export-status").textContent = "";
  $("#export-result").hidden = false;
  $("#zip-link").href = api.downloadUrl(S.job.id, st.zip);
  const hasM4b = Boolean(st.m4b);
  $("#m4b-link").hidden = !hasM4b;
  $("#m4b-hint").hidden = !hasM4b;
  if (hasM4b) $("#m4b-link").href = api.downloadUrl(S.job.id, st.m4b);
  $("#mp3-files-label").hidden = st.files.length === 0;
  const ul = $("#mp3-list");
  ul.replaceChildren(...st.files.map((f) => el("li", {}, el("a", { href: api.downloadUrl(S.job.id, f), text: f }))));
  announce(t("s5.done"));
}

async function pollExport() {
  const bar = $("#export-bar");
  bar.hidden = false;
  $("#export-start").disabled = true;
  try {
    for (;;) {
      const st = await api.exportStatus(S.job.id);
      if (st.state === "running") {
        bar.value = st.total ? (100 * st.done) / st.total : 0;
        $("#export-status").textContent = t("s5.exporting", { done: st.done, total: st.total, current: st.current ? `— ${st.current}` : "" });
      } else if (st.state === "error") {
        throw new ApiError(st.error.code, st.error.detail, st.error.params);
      } else { showExportDone(st); break; }
      await new Promise((r) => setTimeout(r, 700));
    }
  } catch (e) { showError(e); bar.hidden = true; $("#export-status").textContent = ""; } finally { $("#export-start").disabled = false; }
}

/* ------------------------------------------------------------------ init */
function bind() {
  $("#lang").addEventListener("change", async (e) => { await setLang(e.target.value); await rerender(); });
  $("#btn-projects").addEventListener("click", async () => { S.job = null; S.tutorial = false; await goStep(1); });
  $("#btn-tutorial").addEventListener("click", () => $("#tutorial").showModal());
  $("#tut-go").addEventListener("click", async () => {
    S.tutorial = true;
    legalAcceptTutorial();
    await startDemo(currentLang());
  });
  $$("#stepper button").forEach((b) => b.addEventListener("click", () => goStep(Number(b.dataset.step))));
  $$("[data-go]").forEach((b) => b.addEventListener("click", () => goStep(Number(b.dataset.go))));
  $("#legal-accept").checked = safeStorage.get("legal") === "1";
  $("#legal-accept").addEventListener("change", (e) => { safeStorage.set("legal", e.target.checked ? "1" : "0"); applyLegalGate(); });
  $("#file").addEventListener("change", (e) => handleFile(e.target.files[0]));
  const drop = $("#drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));
  $("#demo-es").addEventListener("click", () => startDemo("es"));
  $("#demo-en").addEventListener("click", () => startDemo("en"));

  $("#meta-title").addEventListener("input", (e) => { S.job.book.title = e.target.value; });
  $("#meta-author").addEventListener("input", (e) => { S.job.book.author = e.target.value; });
  $("#meta-lang").addEventListener("change", (e) => { S.job.book.language = e.target.value; });
  $("#ch-title").addEventListener("input", (e) => { const c = selChapter(); if (c) { c.title = e.target.value; renderChapters(); } });
  $("#ch-text").addEventListener("input", (e) => { const c = selChapter(); if (c) { c.text = e.target.value; $("#ch-count").textContent = t("s2.chars", { n: c.text.length.toLocaleString(currentLang()), min: minutesOf(c.text.length) }); } });
  $("#chapter-add").addEventListener("click", () => {
    const c = { id: null, title: t("s2.new_title"), text: t("s2.new_chapter_text"), included: true, _k: `n${++S.keySeq}` };
    S.job.book.chapters.push(c); S.selKey = keyOf(c); renderChapters(); $("#ch-title").focus();
  });
  $("#chapter-del").addEventListener("click", () => {
    const ch = S.job.book.chapters, i = ch.findIndex((c) => keyOf(c) === S.selKey);
    if (i < 0 || ch.length <= 1) return;
    ch.splice(i, 1); S.selKey = keyOf(ch[Math.min(i, ch.length - 1)]); renderChapters();
  });
  $("#s2-next").addEventListener("click", () => goStep(3));

  $("#voice-lang").addEventListener("change", () => { S.settings.voice = ""; guard(loadVoices); });
  $("#speed").addEventListener("input", (e) => { $("#speed-out").textContent = Number(e.target.value).toFixed(2).replace(/0$/, ""); scheduleSave(); });
  ["#pause-p", "#pause-c", "#read-titles", "#speaker"].forEach((s) => $(s).addEventListener("change", scheduleSave));
  $("#pron-add").addEventListener("click", () => { collectSettings(); S.settings.pronunciation.push({ source: "", spoken: "", whole_word: true, case_sensitive: true }); renderPron(); $$(".pron-from").at(-1).focus(); });
  $("#s3-next").addEventListener("click", () => guard(step3Next));
  document.addEventListener("click", (e) => {
    const b = e.target.closest(".help-btn");
    if (!b) return;
    const target = document.getElementById(b.getAttribute("aria-controls"));
    const open = b.getAttribute("aria-expanded") === "true";
    b.setAttribute("aria-expanded", String(!open));
    target.hidden = open;
  });

  $("#gen-start").addEventListener("click", () => generate("start"));
  $("#gen-pause").addEventListener("click", () => generate("pause"));
  $("#gen-cancel").addEventListener("click", () => generate("cancel"));
  $("#s4-next").addEventListener("click", () => goStep(5));

  $("#cover-file").addEventListener("change", (e) => guard(async () => {
    const f = e.target.files[0];
    if (!f) return;
    const job = await api.setCover(S.job.id, f);
    S.job.has_cover = job.has_cover; S.job.book.cover = job.book.cover; renderCover(); e.target.value = "";
  }));
  $("#export-start").addEventListener("click", () => guard(async () => {
    showError(null);
    $("#export-result").hidden = true;
    const formats = [$("#fmt-m4b").checked && "m4b", $("#fmt-mp3").checked && "mp3"].filter(Boolean);
    await api.startExport(S.job.id, formats);
    await pollExport();
  }));
  $("#new-book").addEventListener("click", async () => { S.job = null; S.tutorial = false; await goStep(1); });
}

function legalAcceptTutorial() {
  // El tutorial usa libros de dominio público: no hace falta pedir derechos sobre un libro propio.
  $("#legal-accept").checked = true;
  applyLegalGate();
}

async function rerender() {
  $("#formats").textContent = t("s1.formats", { formats: (S.system?.supported_formats || []).join(" ") });
  renderSystemBanner();
  S.lastStatus = null;
  await goStep(S.step);
}

function renderSystemBanner() {
  const b = $("#sys-banner");
  const sys = S.system;
  if (!sys) { b.hidden = true; return; }
  const missing = [];
  if (!sys.ffmpeg) missing.push(t("sys.ffmpeg_missing"));
  if (!sys.espeak) missing.push(t("sys.espeak_missing"));
  b.hidden = missing.length === 0;
  b.replaceChildren(el("strong", { text: t("sys.title") }), el("ul", {}, missing.map((m) => el("li", { text: m }))), el("p", { text: t("sys.how") }));
}

async function init() {
  const saved = safeStorage.get("lang");
  const lang = saved || "es";
  $("#lang").value = lang;
  await setLang(lang);
  bind();
  try { S.system = await api.system(); } catch (e) { showError(e); }
  renderSystemBanner();
  const m = location.hash.match(/job=([a-z0-9]+)&step=(\d)/);
  if (m) {
    try {
      const job = await api.job(m[1]);
      await openJob(job, Math.min(5, Math.max(1, Number(m[2]))));
      return;
    } catch { /* el proyecto ya no existe: empezar de cero */ }
  }
  await goStep(1);
}

init();
