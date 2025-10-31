(function (window, document) {
  'use strict';
  
  const chartInstances = new Map();
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

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

  function buildGradient(ctx, colors) {
    const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
    colors.forEach(([stop, color]) => gradient.addColorStop(stop, color));
    return gradient;
  }

  function applyThemeOverrides(config, ctx) {
    const isDark = prefersDark.matches;
    const textColor = isDark ? "rgba(248, 250, 252, 0.94)" : "#0f172a";
    const axisColor = isDark ? "rgba(0, 0, 0, 0.95)" : "#1f2937";
    const gridColor = isDark ? "rgba(148, 163, 184, 0.28)" : "rgba(148, 163, 184, 0.24)";
    const tooltipBg = isDark ? "rgba(15, 23, 42, 0.9)" : "rgba(248, 250, 252, 0.95)";
    const tooltipBorder = isDark ? "rgba(148, 163, 184, 0.35)" : "rgba(15, 23, 42, 0.15)";
    const tooltipText = textColor;
    const tickFont = { weight: "600" };

    config.options = config.options || {};

    // Apply theme to scales
    if (config.options?.scales) {
      for (const scale of Object.values(config.options.scales)) {
        if (scale.ticks) {
          scale.ticks.color = axisColor;
          scale.ticks.font = Object.assign({}, scale.ticks.font || {}, tickFont);
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
          scale.title.font = Object.assign({}, scale.title.font || {}, { weight: "600" });
        }
      }
    }

    // Apply theme to plugins
    if (config.options?.plugins?.legend?.labels) {
      config.options.plugins.legend.labels.color = textColor;
      config.options.plugins.legend.labels.font = Object.assign(
        {},
        config.options.plugins.legend.labels.font || {},
        tickFont
      );
    }
    if (config.options?.plugins?.legend) {
      config.options.plugins.legend.labels = config.options.plugins.legend.labels || {};
      config.options.plugins.legend.labels.usePointStyle = true;
    }
    
    if (config.options?.plugins?.title) {
      config.options.plugins.title.color = textColor;
      config.options.plugins.title.font = Object.assign(
        {},
        config.options.plugins.title.font || {},
        { weight: "600" }
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
    tooltip.titleFont = Object.assign({}, tooltip.titleFont || {}, { weight: "600" });
    tooltip.bodyFont = Object.assign({}, tooltip.bodyFont || {}, { weight: "500" });
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
    const existing = chartInstances.get(id);
    if (existing) {
      existing.destroy();
      chartInstances.delete(id);
    }
  }

  function hydrateChart(container, index = 0) {
    const config = parseJSON(container.getAttribute("data-chart-config"));
    if (!config) return;

    const canvas = container.querySelector("canvas");
    if (!canvas) return;

    // Generate unique chart ID
    const chartId = container.dataset.chartId || 
                   canvas.id || 
                   `chart-${Date.now()}-${index}`;
    
    // Clean up existing chart
    destroyChart(chartId);

    const ctx = canvas.getContext("2d");
    
    // Apply theme and styling
    applyThemeOverrides(config, ctx);
    
    // Create new chart instance
    try {
      const instance = new window.Chart(ctx, config);
      chartInstances.set(chartId, instance);
      
      // Store reference on container
      container.dataset.chartId = chartId;
    } catch (error) {
      console.error("overview: Lỗi khởi tạo biểu đồ", error);
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
    chartInstances.forEach((instance, id) => {
      const canvas = instance.canvas;
      if (!canvas || !canvas.isConnected) {
        destroyChart(id);
        return;
      }
      
      const container = canvas.closest("[data-chart-config]");
      if (container) {
        destroyChart(id);
        hydrateChart(container);
      }
    });
  }, 100);

  // Initialize when DOM is ready
  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
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
      const target = targetSelector ? 
        document.querySelector(targetSelector) : elt;
      
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
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        const active = document.activeElement;
        if (active.classList.contains('summary-card') || 
            active.classList.contains('activity-item')) {
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
    destroyChart: destroyChart
  };

  // Start initialization
  init();

})(window, document);
