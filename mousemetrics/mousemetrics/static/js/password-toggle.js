document.addEventListener("DOMContentLoaded", function () {
  const toggleBtns = document.querySelectorAll("[data-hs-toggle-password]");

  toggleBtns.forEach((toggleBtn) => {
    const config = JSON.parse(toggleBtn.dataset.hsTogglePassword);
    const target = document.querySelector(config.target);

    if (!target) return;

    toggleBtn.addEventListener("mousedown", (e) => e.preventDefault());

    toggleBtn.addEventListener("click", () => {
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const isPassword = target.getAttribute("type") === "password";

      target.setAttribute("type", isPassword ? "text" : "password");
      toggleBtn.classList.toggle("hs-password-active");

      const eyeIcon = toggleBtn.querySelector('.eye-icon');
      const eyeSlashIcon = toggleBtn.querySelector('.eye-slash-icon');

      if (eyeIcon && eyeSlashIcon) {
        eyeIcon.classList.toggle('hidden');
        eyeSlashIcon.classList.toggle('hidden');
      }

      requestAnimationFrame(() => {
        target.setSelectionRange(start, end);
        target.focus();
      });
    });
  });
});
