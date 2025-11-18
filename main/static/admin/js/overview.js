(function (window, document) {
  "use strict";
  const chartInstances = new Map();
  const chartContainers = new Map();
  const chartSizeCache = new Map();
  const refreshQueue = new WeakMap();
  const supportsResizeObserver = typeof window.ResizeObserver !== "undefined";
  const resizeObserver = supportsResizeObserver
    ? new window.ResizeObserver((entries) => {
        entries.forEach((entry) => {
          scheduleContainerRefresh(entry.target);
        });
      })
    : null;

  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  );
  const CHART_FONT_STACK =
    "Inter, 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif";
  const CHART_FONT_SIZE = 13;
  const CHART_FONT_SMALL_SIZE = 12;
  const CHART_FONT_WEIGHT = "500";
  const CHART_FONT_WEIGHT_STRONG = "600";

  // Performance optimization

  const debounce = (func, wait) => {
    let timeout;

    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);

        func(...args);
      };

      clearTimeout(timeout);

      timeout = setTimeout(later, wait);
    };
  };

  function parseJSON(value) {
    if (!value) return null;

    try {
      return JSON.parse(value);
    } catch (error) {
      console.error("overview: không thể parse JSON", error);

      return null;
    }
  }

  function setLoadingState(section, isLoading) {
    if (!section) return;

    const container = section.closest(".overview-section");

    if (!container) return;

    // Add loading class with animation if not preferring reduced motion

    if (!prefersReducedMotion.matches) {
      if (isLoading) {
        container.classList.remove("is-loaded");

        container.classList.add("is-loading");
      } else {
        container.classList.remove("is-loading");

        setTimeout(() => {
          container.classList.add("is-loaded");
        }, 50);
      }
    } else {
      // Simple toggle for reduced motion

      container.classList.toggle("is-loading", isLoading);
    }
  }

  function applyChartFontDefaults() {
    const ChartLib = window.Chart;
    if (!ChartLib?.defaults) {
      return;
    }
    const defaults = ChartLib.defaults;
    defaults.font = Object.assign({}, defaults.font || {}, {
      family: CHART_FONT_STACK,
      size: CHART_FONT_SIZE,
      weight: CHART_FONT_WEIGHT,
    });
    defaults.color =
      defaults.color || (prefersDark.matches ? "#f8fafc" : "#0f172a");
  }

  function buildGradient(ctx, colors) {
    const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);

    colors.forEach(([stop, color]) => gradient.addColorStop(stop, color));

    return gradient;
  }

  function applyThemeOverrides(config, ctx) {
    const isDark = prefersDark.matches;

    const textColor = isDark ? "rgba(248, 250, 252, 0.94)" : "#0f172a";

    const axisColor = isDark ? "rgba(0, 0, 0, 0.95)" : "#1f2937";

    const gridColor = isDark
      ? "rgba(148, 163, 184, 0.28)"
      : "rgba(148, 163, 184, 0.24)";

    const tooltipBg = isDark
      ? "rgba(15, 23, 42, 0.9)"
      : "rgba(248, 250, 252, 0.95)";

    const tooltipBorder = isDark
      ? "rgba(148, 163, 184, 0.35)"
      : "rgba(15, 23, 42, 0.15)";

    const tooltipText = textColor;
    const tickFont = {
      weight: CHART_FONT_WEIGHT_STRONG,
      family: CHART_FONT_STACK,
      size: CHART_FONT_SIZE,
    };

    config.options = config.options || {};

    // Apply theme to scales

    if (config.options?.scales) {
      for (const scale of Object.values(config.options.scales)) {
        if (scale.ticks) {
          scale.ticks.color = axisColor;

          scale.ticks.font = Object.assign(
            {},
            scale.ticks.font || {},
            tickFont
          );
        } else {
          scale.ticks = { color: axisColor, font: tickFont };
        }

        if (scale.grid) {
          scale.grid.color = gridColor;
        } else {
          scale.grid = { color: gridColor };
        }

        // Title styling

        if (scale.title) {
          scale.title.color = textColor;
          scale.title.font = Object.assign({}, scale.title.font || {}, {
            weight: CHART_FONT_WEIGHT_STRONG,
            family: CHART_FONT_STACK,
            size: CHART_FONT_SIZE,
          });
        }
      }
    }

    // Apply theme to plugins

    if (config.options?.plugins?.legend) {
      const legend = config.options.plugins.legend;
      legend.labels = legend.labels || {};
      legend.labels.color = textColor;
      legend.labels.font = Object.assign({}, legend.labels.font || {}, {
        family: CHART_FONT_STACK,
        size: CHART_FONT_SIZE,
        weight: CHART_FONT_WEIGHT_STRONG,
      });
      legend.labels.usePointStyle = true;
    }

    if (config.options?.plugins?.title) {
      config.options.plugins.title.color = textColor;

      config.options.plugins.title.font = Object.assign(
        {},

        config.options.plugins.title.font || {},

        {
          weight: CHART_FONT_WEIGHT_STRONG,
          family: CHART_FONT_STACK,
          size: CHART_FONT_SIZE + 1,
        }
      );
    }

    config.options.plugins = config.options.plugins || {};

    const tooltip = config.options.plugins.tooltip || {};

    tooltip.titleColor = tooltip.titleColor || tooltipText;

    tooltip.bodyColor = tooltip.bodyColor || tooltipText;

    tooltip.backgroundColor = tooltip.backgroundColor || tooltipBg;

    tooltip.borderColor = tooltip.borderColor || tooltipBorder;

    tooltip.borderWidth = tooltip.borderWidth || 1;

    tooltip.displayColors = true;

    tooltip.titleFont = Object.assign({}, tooltip.titleFont || {}, {
      weight: CHART_FONT_WEIGHT_STRONG,
      family: CHART_FONT_STACK,
      size: CHART_FONT_SIZE,
    });

    tooltip.bodyFont = Object.assign({}, tooltip.bodyFont || {}, {
      weight: CHART_FONT_WEIGHT,
      family: CHART_FONT_STACK,
      size: CHART_FONT_SMALL_SIZE,
    });

    config.options.plugins.tooltip = tooltip;

    // Apply gradients and colors to datasets

    (config.data?.datasets || []).forEach((dataset, index) => {
      // Apply gradients if specified

      if (dataset.backgroundGradient && ctx) {
        const gradient = buildGradient(ctx, dataset.backgroundGradient);

        dataset.backgroundColor = gradient;

        delete dataset.backgroundGradient;
      }

      if (dataset.borderGradient && ctx) {
        const gradient = buildGradient(ctx, dataset.borderGradient);

        dataset.borderColor = gradient;

        delete dataset.borderGradient;
      }

      // Fallback colors with theme consideration

      if (!dataset.borderColor) {
        const fallbackColors = isDark
          ? ["#818cf8", "#38bdf8", "#34d399", "#fbbf24", "#f472b6"]
          : ["#4338ca", "#0ea5e9", "#10b981", "#f59e0b", "#e11d48"];

        dataset.borderColor = fallbackColors[index % fallbackColors.length];
      }

      if (!dataset.backgroundColor) {
        const fallbackColors = isDark
          ? ["#818cf855", "#38bdf855", "#34d39955", "#fbbf2455", "#f472b655"]
          : ["#4338ca22", "#0ea5e922", "#10b98122", "#f59e0b22", "#e11d4822"];

        dataset.backgroundColor = fallbackColors[index % fallbackColors.length];
      }

      if (!dataset.pointBackgroundColor) {
        dataset.pointBackgroundColor = isDark ? "#f8fafc" : "#0f172a";
      }

      if (!dataset.pointBorderColor) {
        dataset.pointBorderColor = dataset.borderColor;
      }

      if (!dataset.pointHoverBackgroundColor) {
        dataset.pointHoverBackgroundColor = isDark ? "#f8fafc" : "#1f2937";
      }

      if (!dataset.pointHoverBorderColor) {
        dataset.pointHoverBorderColor = dataset.borderColor;
      }

      // Default styling

      if (typeof dataset.borderWidth === "undefined") {
        dataset.borderWidth = 3;
      }

      if (typeof dataset.pointBackgroundColor === "undefined") {
        dataset.pointBackgroundColor = isDark ? "#1e293b" : "#ffffff";
      }

      if (typeof dataset.pointBorderColor === "undefined") {
        dataset.pointBorderColor = dataset.borderColor;
      }

      if (typeof dataset.pointBorderWidth === "undefined") {
        dataset.pointBorderWidth = 2;
      }
    });
  }

  function destroyChart(id) {
    if (!id) return;

    const existing = chartInstances.get(id);

    if (existing) {
      existing.destroy();

      chartInstances.delete(id);
    }

    chartSizeCache.delete(id);

    const container = chartContainers.get(id);

    if (container && resizeObserver) {
      resizeObserver.unobserve(container);
    }

    if (container && container.dataset && container.dataset.chartId === id) {
      delete container.dataset.chartId;
    }

    chartContainers.delete(id);
  }

  function hydrateChart(container, index = 0, chartIdOverride) {
    const config = parseJSON(container.getAttribute("data-chart-config"));

    if (!config) return;

    const canvas = container.querySelector("canvas");

    if (!canvas) return;

    // Generate unique chart ID

    const chartId =
      chartIdOverride ||
      container.dataset.chartId ||
      canvas.id ||
      `chart-${Date.now()}-${index}`;

    // Clean up existing chart

    destroyChart(chartId);

    const ctx = canvas.getContext("2d");

    // Apply theme and styling

    applyChartFontDefaults();

    applyThemeOverrides(config, ctx);

    // Create new chart instance

    try {
      const instance = new window.Chart(ctx, config);

      chartInstances.set(chartId, instance);

      // Store reference on container

      container.dataset.chartId = chartId;

      chartContainers.set(chartId, container);

      const rect = container.getBoundingClientRect();

      chartSizeCache.set(chartId, {
        width: rect.width,

        height: rect.height,
      });

      if (resizeObserver) {
        resizeObserver.observe(container);
      }
    } catch (error) {
      console.error("overview: Lỗi khởi tạo biểu đồ", error);
    }
  }

  function scheduleContainerRefresh(container, forceRebuild = false) {
    if (!container) return;

    const pending = refreshQueue.get(container);

    if (typeof pending !== "undefined") {
      if (forceRebuild && pending === false) {
        refreshQueue.set(container, true);
      }

      return;
    }

    refreshQueue.set(container, forceRebuild);

    requestAnimationFrame(() => {
      const shouldForce = refreshQueue.get(container);

      refreshQueue.delete(container);

      refreshChartContainer(container, shouldForce === true);
    });
  }

  function refreshChartContainer(container, forceRebuild = false) {
    if (!container) return;

    const chartId = container.dataset.chartId;

    const existing = chartId ? chartInstances.get(chartId) : null;

    if (!existing) {
      hydrateChart(container);

      return;
    }

    if (forceRebuild) {
      hydrateChart(container, 0, chartId);

      return;
    }

    const rect = container.getBoundingClientRect();

    const previous = chartId ? chartSizeCache.get(chartId) : null;

    const widthChanged = !previous || Math.abs(previous.width - rect.width) > 8;

    const heightChanged =
      !previous || Math.abs(previous.height - rect.height) > 8;

    chartSizeCache.set(chartId, { width: rect.width, height: rect.height });

    if (widthChanged || heightChanged) {
      hydrateChart(container, 0, chartId);

      return;
    }

    try {
      existing.resize();

      existing.update("none");
    } catch (error) {
      console.error("overview: Khong the cap nhat bieu do", error);

      hydrateChart(container, 0, chartId);
    }
  }

  function initCharts(root = document) {
    const containers = root.querySelectorAll("[data-chart-config]");

    containers.forEach((container, index) => {
      // Use requestAnimationFrame for better performance

      requestAnimationFrame(() => {
        hydrateChart(container, index);
      });
    });
  }

  const refreshAllCharts = debounce(() => {
    chartInstances.forEach((_instance, id) => {
      const container = chartContainers.get(id);

      if (!container || !container.isConnected) {
        destroyChart(id);

        return;
      }

      scheduleContainerRefresh(container);
    });
  }, 150);

  function syncRangeControls() {
    const headerActions = document.querySelector(".chart-header-actions");

    if (!headerActions) return;

    const dropdown = headerActions.querySelector(".chart-range-dropdown");

    if (!dropdown) return;

    const hidden = headerActions.querySelector("#overview-chart-range");

    const range = hidden?.value || dropdown.getAttribute("data-active-range");

    if (!range) return;

    const labelEl = dropdown.querySelector(".btn-range-label");

    let activeLabel = null;

    dropdown.querySelectorAll(".btn-range").forEach((button) => {
      const isActive = button.getAttribute("data-range") === range;

      button.classList.toggle("is-active", isActive);

      button.setAttribute("aria-pressed", isActive ? "true" : "false");

      button.setAttribute("aria-checked", isActive ? "true" : "false");

      if (isActive) {
        activeLabel =
          button.getAttribute("data-label") || button.textContent.trim();
      }
    });

    if (labelEl && activeLabel) {
      labelEl.textContent = activeLabel;
    }

    dropdown.setAttribute("data-active-range", range);

    if (hidden && hidden.value !== range) {
      hidden.value = range;
    }
  }

  // Initialize when DOM is ready

  function init() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        initCharts();

        setupEventListeners();
      });
    } else {
      initCharts();

      setupEventListeners();
    }
  }

  function setupEventListeners() {
    // HTMX event handlers

    document.addEventListener("htmx:beforeRequest", function (event) {
      const elt = event.target;

      if (!(elt instanceof HTMLElement)) return;

      const targetSelector = elt.getAttribute("hx-target");

      const target = targetSelector
        ? document.querySelector(targetSelector)
        : elt;

      setLoadingState(target, true);
    });

    document.addEventListener("htmx:afterSwap", function (event) {
      const target = event.target;

      if (!(target instanceof HTMLElement)) return;

      setLoadingState(target, false);

      // Initialize charts in the new content

      requestAnimationFrame(() => {
        initCharts(target);
      });
    });

    document.addEventListener("overview:lazy-reload", (event) => {
      const detail = event.detail || {};

      const selector = detail.target;

      if (!selector) return;

      const target = document.querySelector(selector);

      if (!target) return;

      const url = target.getAttribute("hx-get");

      if (!url) return;

      const swap = target.getAttribute("hx-swap") || "innerHTML";

      let headers = undefined;

      const headersAttr = target.getAttribute("hx-headers");

      if (headersAttr) {
        try {
          headers = JSON.parse(headersAttr);
        } catch (err) {
          console.warn("overview: invalid hx-headers JSON", err);
        }
      }

      const delay =
        typeof detail.delay === "number" && !Number.isNaN(detail.delay)
          ? detail.delay
          : 800;

      if (!window.htmx || typeof window.htmx.ajax !== "function") {
        console.warn("overview: htmx not available for lazy reload");

        return;
      }

      const values = detail.params ? { ...detail.params } : {};

      const includeSelector = target.getAttribute("hx-include");

      if (includeSelector) {
        document.querySelectorAll(includeSelector).forEach((includeEl) => {
          if (includeEl instanceof HTMLFormElement) {
            const formData = new FormData(includeEl);

            formData.forEach((value, key) => {
              if (values[key] === undefined) {
                values[key] = value;
              }
            });
          } else if (
            includeEl instanceof HTMLInputElement ||
            includeEl instanceof HTMLSelectElement ||
            includeEl instanceof HTMLTextAreaElement
          ) {
            const name = includeEl.name;

            if (name && values[name] === undefined) {
              values[name] = includeEl.value;
            }
          }
        });
      }

      setTimeout(() => {
        window.htmx.ajax("GET", url, {
          target: target,

          swap: swap,

          headers: headers,

          values: Object.keys(values).length ? values : undefined,
        });
      }, delay);
    });

    const headerActionsRoot = document.querySelector(".chart-header-actions");

    if (headerActionsRoot) {
      const dropdown = headerActionsRoot.querySelector(".chart-range-dropdown");

      const hiddenInput = headerActionsRoot.querySelector(
        "#overview-chart-range"
      );

      const toggleBtn = dropdown?.querySelector(".btn-range-toggle");

      const closeMenu = () => {
        if (!dropdown || !toggleBtn) return;

        dropdown.classList.remove("is-open");

        toggleBtn.setAttribute("aria-expanded", "false");
      };

      const openMenu = () => {
        if (!dropdown || !toggleBtn) return;

        dropdown.classList.add("is-open");

        toggleBtn.setAttribute("aria-expanded", "true");
      };

      toggleBtn?.addEventListener("click", (event) => {
        event.preventDefault();

        if (!dropdown) return;

        const isOpen = dropdown.classList.contains("is-open");

        if (isOpen) {
          closeMenu();
        } else {
          openMenu();
        }
      });

      document.addEventListener("click", (event) => {
        if (!dropdown) return;

        if (!dropdown.contains(event.target)) {
          closeMenu();
        }
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          closeMenu();
        }
      });

      dropdown?.addEventListener("click", (event) => {
        const option = event.target.closest(".btn-range");

        if (!option || !(option instanceof HTMLElement)) {
          return;
        }

        const range = option.getAttribute("data-range");

        if (!range) {
          return;
        }

        if (hiddenInput) {
          hiddenInput.value = range;
        }

        if (dropdown) {
          dropdown.setAttribute("data-active-range", range);
        }

        closeMenu();

        syncRangeControls();
      });

      document.addEventListener("overview:update-range", (event) => {
        const range = event.detail?.range;

        if (!range) return;

        if (hiddenInput) {
          hiddenInput.value = range;
        }

        if (dropdown) {
          dropdown.setAttribute("data-active-range", range);
        }

        closeMenu();

        syncRangeControls();
      });
    }

    syncRangeControls();

    // Responsive chart handling

    const resizeHandler = debounce(() => {
      refreshAllCharts();
    }, 150);

    window.addEventListener("resize", resizeHandler);

    // Theme change handling

    if (prefersDark?.addEventListener) {
      prefersDark.addEventListener("change", refreshAllCharts);
    }

    // Reduced motion handling

    if (prefersReducedMotion?.addEventListener) {
      prefersReducedMotion.addEventListener("change", () => {
        // Re-initialize with appropriate animations

        refreshAllCharts();
      });
    }

    // Add keyboard navigation for cards

    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        const active = document.activeElement;

        if (
          active.classList.contains("summary-card") ||
          active.classList.contains("activity-item")
        ) {
          e.preventDefault();

          active.click();
        }
      }
    });
  }

  // Public API

  window.OverviewDashboard = {
    refreshCharts: refreshAllCharts,

    initCharts: initCharts,

    destroyChart: destroyChart,
  };

  // Start initialization

  init();
})(window, document);
