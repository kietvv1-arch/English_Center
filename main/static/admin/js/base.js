// admin/js/base.js (stable)

(function () {
  // Ngăn khởi tạo trùng nếu script được import nhiều lần
  if (document.documentElement.dataset.adminJsInit === "1") return;
  document.documentElement.dataset.adminJsInit = "1";

  // =============================
  // Helpers
  // =============================
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const debounce = (fn, wait = 150) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(null, args), wait);
    };
  };

  const throttle = (fn, wait = 100) => {
    let last = 0;
    return (...args) => {
      const now = Date.now();
      if (now - last >= wait) {
        last = now;
        fn.apply(null, args);
      }
    };
  };

  const getCsrfToken = () => {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  };

  // =============================
  // DOM refs (có null-guard)
  // =============================
  const layout = qs(".layout");
  const sidebar = qs("#sidebar");
  const sidebarToggle = qs("#sidebarToggle");
  const sidebarCloseMobile = qs("#sidebarCloseMobile");
  const sidebarCollapseToggle = qs("#sidebarCollapseToggle");
  const navbarControlToggle = qs("#navbarControlToggle");
  const themeToggle = qs("#themeToggle");
  const footerStatusRefresh = qs("#footerStatusRefresh");

  const MOBILE_OPEN_CLASS = "layout__sidebar--mobile-open";
  const COLLAPSED_CLASS = "layout--sidebar-collapsed";
  const lgUp = window.matchMedia("(min-width: 992px)");

  // =============================
  // Sidebar (mobile + collapsed)
  // =============================
  const isMobileOpen = () =>
    !!(sidebar && sidebar.classList.contains(MOBILE_OPEN_CLASS));

  const openMobileSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.add(MOBILE_OPEN_CLASS);
    document.body.style.overflow = "hidden";
  };

  const closeMobileSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.remove(MOBILE_OPEN_CLASS);
    document.body.style.overflow = "";
  };

  const toggleMobileSidebar = () => {
    if (!sidebar) return;
    if (isMobileOpen()) {
      closeMobileSidebar();
    } else {
      openMobileSidebar();
    }
  };

  // Nút mở/đóng sidebar trên mobile
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", (e) => {
      e.preventDefault();
      toggleMobileSidebar();
    });
  }
  if (sidebarCloseMobile) {
    sidebarCloseMobile.addEventListener("click", (e) => {
      e.preventDefault();
      closeMobileSidebar();
    });
  }

  // Click outside để đóng sidebar (mobile) — chỉ 1 listener
  document.addEventListener("click", (e) => {
    if (!sidebar || !sidebarToggle) return;
    if (lgUp.matches) return; // chỉ chạy trên mobile
    const clickInsideSidebar = sidebar.contains(e.target);
    const clickToggle = sidebarToggle.contains(e.target);
    if (!clickInsideSidebar && !clickToggle && isMobileOpen()) {
      closeMobileSidebar();
    }
  });

  // Thu gọn sidebar (desktop)
  const setCollapsed = (val) => {
    if (!layout) return;
    layout.classList.toggle(COLLAPSED_CLASS, !!val);
    localStorage.setItem("admin_sidebar_collapsed", !!val ? "1" : "0");
  };

  if (sidebarCollapseToggle) {
    sidebarCollapseToggle.addEventListener("click", (e) => {
      e.preventDefault();
      const next = !(layout && layout.classList.contains(COLLAPSED_CLASS));
      setCollapsed(next);
    });
  }

  // Khôi phục trạng thái collapsed từ localStorage
  (() => {
    const saved = localStorage.getItem("admin_sidebar_collapsed");
    if (saved === "1") setCollapsed(true);
  })();

  // Reset state khi đổi viewport
  const handleViewportChange = () => {
    // Khi lên desktop, đảm bảo sidebar mobile đóng
    if (lgUp.matches) {
      closeMobileSidebar();
    }
  };
  lgUp.addEventListener("change", handleViewportChange);

  // =============================
  // Navbar controls (tùy dự án)
  // =============================
  if (navbarControlToggle) {
    navbarControlToggle.addEventListener("click", (e) => {
      // ví dụ: mở dropdown cài đặt; để trống nếu bạn xử lý nơi khác
    });
  }

  // =============================
  // Theme toggle (light/dark)
  // =============================
  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    // cập nhật aria-pressed + icon nếu có
    if (themeToggle) {
      themeToggle.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      const icon = themeToggle.querySelector("i");
      if (icon) {
        // FA v6: fa-solid fa-sun / fa-moon
        icon.className = theme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
      }
    }
  };

  const detectInitialTheme = () => {
    const saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") return saved;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "dark" : "light";
  };

  applyTheme(detectInitialTheme());

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme") || "light";
      const next = cur === "dark" ? "light" : "dark";
      localStorage.setItem("theme", next);
      applyTheme(next);
    });
  }

  // =============================
  // Bootstrap (optional safety)
  // =============================
  if (window.bootstrap) {
    // Tooltips
    qsa('[data-bs-toggle="tooltip"]').forEach((el) => {
      try {
        new bootstrap.Tooltip(el);
      } catch {}
    });
    // Dropdown hover (nếu bạn cần hover trên lg+)
    const dropdowns = qsa(".navbar .dropdown");
    const onEnter = (e) => {
      if (!lgUp.matches) return;
      const toggle = qs('[data-bs-toggle="dropdown"]', e.currentTarget);
      if (!toggle) return;
      const inst = bootstrap.Dropdown.getOrCreateInstance(toggle);
      inst.show();
    };
    const onLeave = (e) => {
      if (!lgUp.matches) return;
      const toggle = qs('[data-bs-toggle="dropdown"]', e.currentTarget);
      if (!toggle) return;
      const inst = bootstrap.Dropdown.getOrCreateInstance(toggle);
      inst.hide();
    };
    dropdowns.forEach((dd) => {
      dd.addEventListener("mouseenter", onEnter);
      dd.addEventListener("mouseleave", onLeave);
    });
  }

  // =============================
  // Footer status refresh (tùy)
  // =============================
  // Nếu bạn dùng nút #footerStatusRefresh để gọi API trạng thái, ta cung cấp tiện ích gọi lại.
  const refreshStatus = () => {
    if (footerStatusRefresh) footerStatusRefresh.click();
  };

  // =============================
  // Performance log (optional)
  // =============================
  window.addEventListener("load", () => {
    const [nav] = performance.getEntriesByType("navigation");
    const dur = nav ? nav.duration : 0;
    if (dur) {
      // eslint-disable-next-line no-console
      console.log(`Page loaded in ~${Math.round(dur)}ms`);
      if (dur > 3000) console.warn("Page load is slow (>3s) — consider optimization.");
    }
  });

  // =============================
  // Expose utils (hạn chế global)
  // =============================
  window.adminUtils = {
    debounce,
    throttle,
    refreshStatus,
    getCsrfToken,
  };
})();
