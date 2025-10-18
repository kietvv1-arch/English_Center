/* global gsap, bootstrap */

// ========= BG animation, floating cards, reveal on scroll, nav collapse (giữ nguyên) =========
document.addEventListener("DOMContentLoaded", () => {
  const bgContainer = document.querySelector(".hero__background");

  if (bgContainer && typeof gsap !== "undefined") {
    for (let i = 0; i < 15; i += 1) {
      const element = document.createElement("div");
      element.classList.add("bg-element");

      const size = Math.random() * 100 + 20;
      element.style.width = `${size}px`;
      element.style.height = `${size}px`;
      element.style.left = `${Math.random() * 100}%`;
      element.style.top = `${Math.random() * 100}%`;

      bgContainer.appendChild(element);

      gsap.to(element, {
        x: Math.random() * 100 - 50,
        y: Math.random() * 100 - 50,
        rotation: Math.random() * 360,
        duration: Math.random() * 10 + 10,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    }
  }

  if (typeof gsap !== "undefined") {
    gsap.to(".floating-card", {
      y: 20,
      duration: 3,
      repeat: -1,
      yoyo: true,
      ease: "sine.inOut",
      stagger: 0.5,
    });
  }

  const observer = new IntersectionObserver(
    (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add("visible")),
    { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
  );
  document.querySelectorAll(".animate-on-scroll").forEach((el) => observer.observe(el));

  const navCollapseEl = document.getElementById("mainNav");
  if (navCollapseEl && typeof bootstrap !== "undefined") {
    document.querySelectorAll(".site-nav .nav-link").forEach((link) => {
      link.addEventListener("click", () => {
        const collapse = bootstrap.Collapse.getInstance(navCollapseEl);
        if (collapse && navCollapseEl.classList.contains("show")) collapse.hide();
      });
    });
  }
});

// ===================== GRADUATES: hover blur/dim + slide-up panel =====================
(function () {
  const cards = document.querySelectorAll(".graduate-card , .teacher-card");
  if (!cards.length) return;

  // Click ngoài để đóng trên mobile/touch
  document.addEventListener("click", (e) => {
    const card = e.target.closest(".graduate-card , .teacher-card");
    if (!card) {
      cards.forEach((c) => c.classList.remove("is-active"));
      return;
    }
    // Toggle trên thiết bị không hỗ trợ hover
    const isTouch = window.matchMedia("(hover: none)").matches;
    if (isTouch) {
      const active = card.classList.contains("is-active");
      cards.forEach((c) => c.classList.remove("is-active"));
      if (!active) card.classList.add("is-active");
    }
  });

  // A11y: bàn phím mở/đóng panel
  cards.forEach((card) => {
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const active = card.classList.contains("is-active");
        cards.forEach((c) => c.classList.remove("is-active"));
        if (!active) card.classList.add("is-active");
      }
      if (e.key === "Escape") card.classList.remove("is-active");
    });
  });
})();
