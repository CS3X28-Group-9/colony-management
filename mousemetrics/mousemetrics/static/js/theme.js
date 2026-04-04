(function () {
  const STORAGE_KEY = "labsafe-color-scheme";

  function getStoredTheme() {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
    return "system";
  }

  function isDarkAppearance(theme) {
    if (theme === "dark") return true;
    if (theme === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function applyTheme(theme) {
    const actual =
      theme === undefined ? getStoredTheme() : theme;
    if (theme !== undefined) {
      localStorage.setItem(STORAGE_KEY, actual);
    }
    document.documentElement.dataset.colorScheme = actual;
    document.documentElement.classList.toggle("dark", isDarkAppearance(actual));
  }

  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => {
      if (getStoredTheme() === "system") applyTheme("system");
    });

  document.addEventListener("DOMContentLoaded", () => {
    const sel = document.getElementById("labsafe-color-scheme-select");
    if (sel) {
      sel.value = getStoredTheme();
      sel.addEventListener("change", () => applyTheme(sel.value));
    }
  });
})();
