// admin/js/base.js

document.addEventListener('DOMContentLoaded', function() {
    // =============================================
    // Global Variables
    // =============================================
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarCloseMobile = document.getElementById('sidebarCloseMobile');
    const sidebarCollapseToggle = document.getElementById('sidebarCollapseToggle');
    const navbarControlToggle = document.getElementById('navbarControlToggle');
    const themeToggle = document.getElementById('themeToggle');
    const layout = document.querySelector('.layout');
    const footerStatusRefresh = document.getElementById('footerStatusRefresh');
    let setMobileSidebarState = null;
    let closeMobileSidebar = null;

    // =============================================
    // Sidebar Functionality
    // =============================================

    // Mobile sidebar toggle
    if (sidebar && sidebarToggle) {
        setMobileSidebarState = isOpen => {
            sidebar.classList.toggle('layout__sidebar--mobile-open', isOpen);
            sidebar.setAttribute('data-mobile-open', isOpen ? 'true' : 'false');
            sidebarToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            document.body.style.overflow = isOpen ? 'hidden' : '';
        };

        const toggleSidebar = () => {
            const isOpen = !sidebar.classList.contains('layout__sidebar--mobile-open');
            setMobileSidebarState(isOpen);
        };

        closeMobileSidebar = () => {
            if (sidebar.classList.contains('layout__sidebar--mobile-open')) {
                setMobileSidebarState(false);
            }
        };

        setMobileSidebarState(false);

        sidebarToggle.addEventListener('click', toggleSidebar);

        // Mobile sidebar close
        if (sidebarCloseMobile) {
            sidebarCloseMobile.addEventListener('click', closeMobileSidebar);
        }

        document.addEventListener('click', function(event) {
            if (
                window.innerWidth < 992 &&
                !sidebar.contains(event.target) &&
                !sidebarToggle.contains(event.target)
            ) {
                closeMobileSidebar();
            }
        });

        window.addEventListener('resize', throttle(() => {
            if (window.innerWidth >= 992) {
                setMobileSidebarState(false);
            }
        }, 150));

        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                closeMobileSidebar();
            }
        });
    }

    // Sidebar collapse toggle (desktop)
    if (sidebarCollapseToggle && layout) {
        sidebarCollapseToggle.addEventListener('click', function() {
            const isCollapsed = layout.classList.toggle('layout--sidebar-collapsed');
            this.setAttribute('aria-pressed', isCollapsed);
            
            // Update icon rotation
            const icon = this.querySelector('i');
            if (icon) {
                icon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
            }

            // Save state to localStorage
            localStorage.setItem('sidebarCollapsed', isCollapsed);
        });
    }

    // Close sidebar when clicking on nav links on mobile
    const navLinks = document.querySelectorAll('.layout__nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                if (typeof setMobileSidebarState === 'function') {
                    setMobileSidebarState(false);
                } else if (sidebar) {
                    sidebar.classList.remove('layout__sidebar--mobile-open');
                    document.body.style.overflow = '';
                }
            }
        });
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth < 992 && 
            !sidebar.contains(event.target) && 
            !sidebarToggle.contains(event.target) &&
            sidebar.classList.contains('layout__sidebar--mobile-open')) {
            sidebar.classList.remove('layout__sidebar--mobile-open');
            document.body.style.overflow = '';
        }
    });

    // =============================================
    // Theme Management
    // =============================================

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            this.setAttribute('aria-pressed', newTheme === 'dark');
            
            // Update icon
            const icon = this.querySelector('i');
            if (icon) {
                icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }

            // Save theme preference
            localStorage.setItem('theme', newTheme);
            
            // Dispatch theme change event
            window.dispatchEvent(new CustomEvent('themeChange', { detail: { theme: newTheme } }));
        });
    }

    // =============================================
    // Dropdown Enhancements
    // =============================================

    // Enhanced dropdown interactions
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');

        if (toggle && menu) {
            // Add smooth animation
            menu.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
            
            // Handle hover for desktop
            if (window.innerWidth >= 992) {
                dropdown.addEventListener('mouseenter', function() {
                    const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
                    if (!bsDropdown) {
                        new bootstrap.Dropdown(toggle).show();
                    } else {
                        bsDropdown.show();
                    }
                });

                dropdown.addEventListener('mouseleave', function() {
                    const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
                    if (bsDropdown) {
                        setTimeout(() => {
                            if (!dropdown.matches(':hover')) {
                                bsDropdown.hide();
                            }
                        }, 100);
                    }
                });
            }
        }
    });

    // =============================================
    // Search Enhancement
    // =============================================

    const searchForm = document.querySelector('.layout__search');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[type="search"]');
        
        // Add debounced search
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (this.value.length >= 2 || this.value.length === 0) {
                    searchForm.submit();
                }
            }, 500);
        });

        // Add keyboard shortcut (Ctrl+K or Cmd+K)
        document.addEventListener('keydown', function(event) {
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                searchInput.focus();
            }
        });

        // Show keyboard shortcut hint
        if (navigator.userAgent.indexOf('Mac') !== -1) {
            searchInput.placeholder = 'Tìm kiếm nhanh... (⌘K)';
        } else {
            searchInput.placeholder = 'Tìm kiếm nhanh... (Ctrl+K)';
        }
    }

    // =============================================
    // Notification Badge Animation
    // =============================================

    const notificationBadges = document.querySelectorAll('.icon-button__badge');
    notificationBadges.forEach(badge => {
        if (parseInt(badge.textContent) > 0) {
            // Add pulse animation for new notifications
            badge.style.animation = 'pulse 2s infinite';
        }
    });

    // =============================================
    // Footer Status System
    // =============================================

    if (footerStatusRefresh) {
        let statusRefreshInterval;
        const statusUrl = document.querySelector('.layout__footer').dataset.statusUrl;
        const statusInterval = parseInt(document.querySelector('.layout__footer').dataset.statusInterval) || 60000;

        // Auto-refresh status if URL is provided
        if (statusUrl) {
            statusRefreshInterval = setInterval(refreshStatus, statusInterval);
            footerStatusRefresh.classList.remove('d-none');
        }

        footerStatusRefresh.addEventListener('click', function() {
            refreshStatus(true);
        });

        async function refreshStatus(manual = false) {
            if (!statusUrl) return;

            const button = footerStatusRefresh;
            const originalHtml = button.innerHTML;
            
            if (manual) {
                button.setAttribute('aria-busy', 'true');
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                button.disabled = true;
            }

            try {
                const response = await fetch(statusUrl);
                const data = await response.json();

                updateStatusIndicators(data);
                
                if (manual) {
                    showToast('Status updated successfully', 'success');
                }
            } catch (error) {
                console.error('Failed to refresh status:', error);
                if (manual) {
                    showToast('Failed to update status', 'error');
                }
            } finally {
                if (manual) {
                    button.setAttribute('aria-busy', 'false');
                    button.innerHTML = originalHtml;
                    button.disabled = false;
                }
            }
        }

        function updateStatusIndicators(data) {
            // Update service status indicators
            const services = ['celery', 'redis', 'smtp'];
            services.forEach(service => {
                const indicator = document.querySelector(`[data-service="${service}"]`);
                if (indicator && data[`${service}_status`]) {
                    const status = data[`${service}_status`];
                    indicator.setAttribute('data-status', status);
                    indicator.className = `status-indicator status-indicator--${status}`;
                    
                    // Update dot color
                    const dot = indicator.querySelector('.status-indicator__dot');
                    if (dot) {
                        dot.style.backgroundColor = getStatusColor(status);
                    }
                }
            });

            // Update storage info
            if (data.storage_db_usage) {
                const dbElement = document.querySelector('[data-footer-field="storageDb"]');
                if (dbElement) dbElement.textContent = data.storage_db_usage;
            }
            if (data.storage_media_usage) {
                const mediaElement = document.querySelector('[data-footer-field="storageMedia"]');
                if (mediaElement) mediaElement.textContent = data.storage_media_usage;
            }
        }

        function getStatusColor(status) {
            const colors = {
                healthy: '#10b981',
                degraded: '#f59e0b',
                down: '#ef4444',
                unknown: '#94a3b8'
            };
            return colors[status] || colors.unknown;
        }
    }

    // =============================================
    // Toast Notification System
    // =============================================

    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.innerHTML = `
            <div class="toast__content">
                <i class="toast__icon ${getToastIcon(type)}"></i>
                <span class="toast__message">${message}</span>
            </div>
            <button class="toast__close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        toastContainer.appendChild(toast);

        // Animate in
        setTimeout(() => toast.classList.add('toast--show'), 10);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('toast--show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    function getToastIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    // =============================================
    // Loading States
    // =============================================

    // Add loading state to all buttons with href
    document.addEventListener('click', function(event) {
        const button = event.target.closest('button, a');
        if (button && button.getAttribute('href') && !button.getAttribute('aria-busy')) {
            const originalText = button.innerHTML;
            button.setAttribute('aria-busy', 'true');
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            button.disabled = true;

            // Restore after 30 seconds if still loading
            setTimeout(() => {
                if (button.getAttribute('aria-busy') === 'true') {
                    button.setAttribute('aria-busy', 'false');
                    button.innerHTML = originalText;
                    button.disabled = false;
                    showToast('Request timed out', 'warning');
                }
            }, 30000);
        }
    });

    // =============================================
    // Responsive Behavior
    // =============================================

    function handleResize() {
        // Auto-close mobile sidebar when resizing to desktop
        if (window.innerWidth >= 992) {
            sidebar.classList.remove('layout__sidebar--mobile-open');
            document.body.style.overflow = '';
        }

        // Update dropdown behavior based on screen size
        const dropdowns = document.querySelectorAll('.dropdown');
        dropdowns.forEach(dropdown => {
            if (window.innerWidth >= 992) {
                dropdown.classList.add('dropdown--hover');
            } else {
                dropdown.classList.remove('dropdown--hover');
            }
        });
    }

    window.addEventListener('resize', debounce(handleResize, 250));

    // =============================================
    // Utility Functions
    // =============================================

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }

    // =============================================
    // Initialize on Load
    // =============================================

    // Restore sidebar state
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebarCollapsed && layout) {
        layout.classList.add('layout--sidebar-collapsed');
        if (sidebarCollapseToggle) {
            sidebarCollapseToggle.setAttribute('aria-pressed', 'true');
            const icon = sidebarCollapseToggle.querySelector('i');
            if (icon) {
                icon.style.transform = 'rotate(180deg)';
            }
        }
    }

    // Restore theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    if (themeToggle) {
        themeToggle.setAttribute('aria-pressed', savedTheme === 'dark');
        const icon = themeToggle.querySelector('i');
        if (icon) {
            icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add CSS for animations
    addCustomStyles();

    // =============================================
    // Custom Styles Injection
    // =============================================

    function addCustomStyles() {
        const styles = `
            <style>
                /* Toast styles */
                .toast-container {
                    position: fixed;
                    top: 80px;
                    right: 20px;
                    z-index: 9999;
                    max-width: 400px;
                }

                .toast {
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                    border-radius: var(--border-radius);
                    padding: var(--spacing-md);
                    margin-bottom: var(--spacing-sm);
                    box-shadow: var(--shadow-lg);
                    transform: translateX(100%);
                    opacity: 0;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: var(--spacing-md);
                }

                .toast--show {
                    transform: translateX(0);
                    opacity: 1;
                }

                .toast--success {
                    border-left: 4px solid var(--success-color);
                }

                .toast--error {
                    border-left: 4px solid var(--danger-color);
                }

                .toast--warning {
                    border-left: 4px solid var(--warning-color);
                }

                .toast--info {
                    border-left: 4px solid var(--info-color);
                }

                .toast__content {
                    display: flex;
                    align-items: center;
                    gap: var(--spacing-sm);
                    flex: 1;
                }

                .toast__icon {
                    font-size: var(--font-size-lg);
                }

                .toast--success .toast__icon {
                    color: var(--success-color);
                }

                .toast--error .toast__icon {
                    color: var(--danger-color);
                }

                .toast--warning .toast__icon {
                    color: var(--warning-color);
                }

                .toast--info .toast__icon {
                    color: var(--info-color);
                }

                .toast__close {
                    background: none;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                    padding: var(--spacing-xs);
                    border-radius: var(--border-radius-sm);
                    transition: var(--transition);
                }

                .toast__close:hover {
                    background: var(--gray-100);
                    color: var(--text-primary);
                }

                /* Pulse animation for badges */
                @keyframes pulse {
                    0% {
                        transform: scale(1);
                        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
                    }
                    50% {
                        transform: scale(1.05);
                    }
                    70% {
                        transform: scale(1);
                        box-shadow: 0 0 0 6px rgba(239, 68, 68, 0);
                    }
                    100% {
                        transform: scale(1);
                        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
                    }
                }

                /* Smooth transitions for dropdowns */
                .dropdown-menu {
                    transition: opacity 0.2s ease, transform 0.2s ease !important;
                }

                .dropdown-menu.show {
                    animation: dropdownSlideIn 0.2s ease;
                }

                @keyframes dropdownSlideIn {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                /* Loading spinner */
                .fa-spinner {
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }

                /* Mobile sidebar overlay */
                @media (max-width: 991.98px) {
                    .layout__sidebar--mobile-open {
                        transform: translateX(0) !important;
                    }
                    
                    .layout__sidebar--mobile-open::before {
                        content: '';
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background: rgba(0, 0, 0, 0.5);
                        z-index: -1;
                    }
                }
            </style>
        `;
        document.head.insertAdjacentHTML('beforeend', styles);
    }

    // =============================================
    // Error Handling
    // =============================================

    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        showToast('An error occurred', 'error');
    });

    // =============================================
    // Performance Monitoring
    // =============================================

    // Log page load time
    window.addEventListener('load', function() {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log(`Page loaded in ${loadTime}ms`);
        
        if (loadTime > 3000) {
            console.warn('Page load time is slow, consider optimization');
        }
    });

    // Export utility functions for global use
    window.adminUtils = {
        showToast,
        debounce,
        throttle,
        refreshStatus: () => footerStatusRefresh && footerStatusRefresh.click()
    };
});

// Make functions available globally for HTML onclick handlers
function refreshStatus() {
    const button = document.getElementById('footerStatusRefresh');
    if (button) button.click();
}
