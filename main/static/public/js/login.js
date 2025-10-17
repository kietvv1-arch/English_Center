/* global gsap, bootstrap */

const loginForm = () => ({
    submitting: false,
});

document.addEventListener("DOMContentLoaded", () => {
    const bgContainer = document.querySelector(".login-hero__background");

    if (bgContainer) {
        for (let i = 0; i < 20; i += 1) {
            const element = document.createElement("div");
            element.classList.add("bg-element");

            const size = Math.random() * 80 + 30;
            element.style.width = `${size}px`;
            element.style.height = `${size}px`;
            element.style.left = `${Math.random() * 100}%`;
            element.style.top = `${Math.random() * 100}%`;

            bgContainer.appendChild(element);

            gsap.to(element, {
                y: Math.random() * 80 - 40,
                x: Math.random() * 80 - 40,
                duration: Math.random() * 12 + 12,
                repeat: -1,
                yoyo: true,
                ease: "sine.inOut",
            });
        }
    }

    gsap.from(".login-hero__content", {
        y: 40,
        opacity: 0,
        duration: 1,
        ease: "power3.out",
        delay: 0.2,
    });

    gsap.from(".login-card", {
        y: 60,
        opacity: 0,
        duration: 1,
        ease: "power3.out",
        delay: 0.35,
    });

    const navCollapseEl = document.getElementById("loginNav");
    if (navCollapseEl && typeof bootstrap !== "undefined") {
        document.querySelectorAll(".site-nav .nav-link").forEach((link) => {
            link.addEventListener("click", () => {
                const collapse = bootstrap.Collapse.getInstance(navCollapseEl);
                if (collapse && navCollapseEl.classList.contains("show")) {
                    collapse.hide();
                }
            });
        });
    }
});

document.addEventListener("htmx:afterRequest", (event) => {
    const path = event.detail?.requestConfig?.path;

    if (path === "/auth/login") {
        const target = document.getElementById("login-response");
        if (target) {
            target.innerHTML =
                '<div class="alert alert-success mt-3">Đăng nhập thành công! Đang chuyển hướng tới bảng điều khiển...</div>';
        }
    }
});
