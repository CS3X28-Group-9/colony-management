(function() {
  'use strict';

  let notificationState = {
    isOpen: false,
    button: null,
    menu: null,
    container: null
  };

  function toggleNotificationDropdown(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    if (!notificationState.menu || !notificationState.button) {
      initNotificationDropdown();
      if (!notificationState.menu || !notificationState.button) {
        return;
      }
    }

    if (notificationState.isOpen) {
      closeDropdown();
    } else {
      openDropdown();
    }
  }

  function openDropdown() {
    if (!notificationState.menu || !notificationState.button) return;

    notificationState.menu.classList.remove('hidden');
    void notificationState.menu.offsetHeight;
    notificationState.menu.classList.remove('opacity-0');
    notificationState.menu.classList.add('opacity-100');
    notificationState.button.setAttribute('aria-expanded', 'true');
    notificationState.isOpen = true;
  }

  function closeDropdown() {
    if (!notificationState.menu || !notificationState.button) return;

    notificationState.menu.classList.add('opacity-0');
    notificationState.menu.classList.remove('opacity-100');
    setTimeout(() => {
      if (notificationState.menu && notificationState.menu.classList.contains('opacity-0')) {
        notificationState.menu.classList.add('hidden');
      }
    }, 200);
    notificationState.button.setAttribute('aria-expanded', 'false');
    notificationState.isOpen = false;
  }

  function initNotificationDropdown() {
    notificationState.button = document.getElementById('notification-dropdown');
    notificationState.container = document.getElementById('notification-container');
    notificationState.menu = document.getElementById('notification-menu');

    if (!notificationState.button || !notificationState.menu) {
      return;
    }

    document.addEventListener('click', function(e) {
      if (notificationState.isOpen && notificationState.container && !notificationState.container.contains(e.target)) {
        closeDropdown();
      }
    });

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && notificationState.isOpen) {
        closeDropdown();
      }
    });
  }

  window.toggleNotificationDropdown = toggleNotificationDropdown;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNotificationDropdown);
  } else {
    initNotificationDropdown();
  }
})();
