/* global gsap, bootstrap */

const state = {
  animateObserver: null,
  cardsDelegated: false,
};

const cardSelector = ".graduate-card, .teacher-card";

function initHeroBackground() {
  const bgContainer = document.querySelector(".hero__background");

  if (!bgContainer || typeof gsap === "undefined") return;

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

function initFloatingCards() {
  if (typeof gsap === "undefined") return;
  gsap.to(".floating-card", {
    y: 20,
    duration: 3,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut",
    stagger: 0.5,
  });
}

function initAnimateOnScroll(root = document) {
  const elements =
    root && typeof root.querySelectorAll === "function"
      ? root.querySelectorAll(".animate-on-scroll")
      : [];

  if (!("IntersectionObserver" in window)) {
    elements.forEach((el) => el.classList.add("visible"));
    return;
  }

  if (!state.animateObserver) {
    state.animateObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            state.animateObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );
  }

  elements.forEach((el) => {
    state.animateObserver.observe(el);

    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      el.classList.add("visible");
    }
  });
}

function initCarousels(root = document) {
  if (typeof bootstrap === "undefined" || typeof root.querySelectorAll !== "function") return;

  root.querySelectorAll(".carousel").forEach((carouselEl) => {
    const instance = bootstrap.Carousel.getOrCreateInstance(carouselEl);
    const shouldCycle =
      carouselEl.getAttribute("data-bs-ride") === "carousel" ||
      carouselEl.dataset.bsRide === "carousel";
    if (shouldCycle && typeof instance.cycle === "function") {
      instance.cycle();
    }
  });
}

function initNavCollapse() {
  const navCollapseEl = document.getElementById("mainNav");
  if (!navCollapseEl || typeof bootstrap === "undefined") return;

  document.querySelectorAll(".site-nav .nav-link").forEach((link) => {
    link.addEventListener("click", () => {
      const collapse = bootstrap.Collapse.getInstance(navCollapseEl);
      if (collapse && navCollapseEl.classList.contains("show")) {
        collapse.hide();
      }
    });
  });
}

function initInteractiveCards() {
  if (state.cardsDelegated) return;
  state.cardsDelegated = true;

  document.addEventListener("click", (event) => {
    const card = event.target.closest(cardSelector);
    const cards = document.querySelectorAll(cardSelector);

    if (!card) {
      cards.forEach((c) => c.classList.remove("is-active"));
      return;
    }

    const isTouch = window.matchMedia("(hover: none)").matches;
    if (isTouch) {
      const active = card.classList.contains("is-active");
      cards.forEach((c) => c.classList.remove("is-active"));
      if (!active) card.classList.add("is-active");
    }
  });

  document.addEventListener("keydown", (event) => {
    const card = event.target.closest(cardSelector);
    if (!card) return;

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const cards = document.querySelectorAll(cardSelector);
      const active = card.classList.contains("is-active");
      cards.forEach((c) => c.classList.remove("is-active"));
      if (!active) card.classList.add("is-active");
    }

    if (event.key === "Escape") {
      card.classList.remove("is-active");
    }
  });
}

function initDynamicSection(root = document) {
  initAnimateOnScroll(root);
  initCarousels(root);
}

document.addEventListener("DOMContentLoaded", () => {
  initHeroBackground();
  initFloatingCards();
  initNavCollapse();
  initInteractiveCards();
  initDynamicSection(document);
});

if (window.htmx && typeof window.htmx.on === "function") {
  window.htmx.on("htmx:afterSwap", (event) => {
    const target = (event.detail && event.detail.target) || event.target || document;
    initDynamicSection(target);
  });
} else {
  document.body.addEventListener(
    "htmx:afterSwap",
    (event) => {
      const target = (event.detail && event.detail.target) || event.target || document;
      initDynamicSection(target);
    },
    { once: false }
  );
}
