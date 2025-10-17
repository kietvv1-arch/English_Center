/* global gsap, bootstrap */

document.addEventListener("DOMContentLoaded", () => {
    const bgContainer = document.querySelector(".hero__background");

    if (bgContainer) {
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

    gsap.to(".floating-card", {
        y: 20,
        duration: 3,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
        stagger: 0.5,
    });

    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px",
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
            }
        });
    }, observerOptions);

    document.querySelectorAll(".animate-on-scroll").forEach((element) => {
        observer.observe(element);
    });

    const navCollapseEl = document.getElementById("mainNav");
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

