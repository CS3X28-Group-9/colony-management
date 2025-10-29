document.addEventListener("DOMContentLoaded", function () {
  const toggleBtn = document.querySelector("[data-hs-toggle-password]");
  if (!toggleBtn) return;

  const config = JSON.parse(toggleBtn.dataset.hsTogglePassword);
  const target = document.querySelector(config.target);

  if (!target) return;

  toggleBtn.addEventListener("mousedown", (e) => e.preventDefault());

  toggleBtn.addEventListener("click", () => {
    const start = target.selectionStart;
    const end = target.selectionEnd;
    const isPassword = target.getAttribute("type") === "password";

    target.setAttribute("type", isPassword ? "text" : "password");

    requestAnimationFrame(() => {
      target.setSelectionRange(start, end);
      target.focus();
    });
  });
});
