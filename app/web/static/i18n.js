// Traducciones: todas las cadenas viven en i18n/<idioma>.json
let dict = {};
let lang = "es";

export const currentLang = () => lang;

export async function setLang(l) {
  const res = await fetch(`i18n/${l}.json`);
  dict = await res.json();
  lang = l;
  document.documentElement.lang = l;
  try { localStorage.setItem("lang", l); } catch { /* sin almacenamiento: no pasa nada */ }
  applyStatic();
}

export function t(key, params = {}) {
  const s = dict[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (m, k) => (params[k] ?? m));
}

export function applyStatic(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll("[data-i18n-attr]").forEach((el) => {
    el.dataset.i18nAttr.split(";").forEach((pair) => {
      const [attr, key] = pair.split("=");
      el.setAttribute(attr.trim(), t(key.trim()));
    });
  });
}

export function fmtDuration(sec) {
  if (sec == null || !isFinite(sec)) return "—";
  sec = Math.max(0, Math.round(sec));
  if (sec < 60) return `${sec} s`;
  const m = Math.round(sec / 60);
  if (m < 60) return `${m} ${t("common.min")}`;
  const h = Math.floor(m / 60);
  return `${h} ${t("common.h")} ${m % 60} ${t("common.min")}`;
}

export function fmtBytes(b) {
  if (!b) return "—";
  if (b < 1e9) return `${Math.max(1, Math.round(b / 1e6))} ${t("common.mb")}`;
  return `${(b / 1e9).toFixed(1)} GB`;
}
