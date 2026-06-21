document.addEventListener("DOMContentLoaded", function() {
    console.log("GLAND Admin Polish active: Correcting AI template errors.");

    // Fix Floating Logout Button -> Pindahkan ke dalam Sidebar secara rapi
    const floatingLogout = document.querySelector('.floating-logout, #logout-btn-floating');
    const sidebar = document.querySelector('aside, .sidebar, #sidebar');
    
    if (floatingLogout && sidebar) {
        const sidebarNav = sidebar.querySelector('nav, .sidebar-menu, ul') || sidebar;
        const logoutWrapper = document.createElement('div');
        logoutWrapper.style.padding = '20px';
        logoutWrapper.style.marginTop = 'auto';
        
        // Transform button style
        floatingLogout.className = 'btn btn-secondary w-100';
        floatingLogout.style.position = 'static';
        floatingLogout.style.display = 'block';
        
        logoutWrapper.appendChild(floatingLogout);
        sidebar.appendChild(logoutWrapper);
    }

    // Refactor Real-time Messages Workflow CSS Injection secara halus
    const msgCards = document.querySelectorAll('.message-card, .msg-item');
    msgCards.forEach(card => {
        card.style.borderRadius = 'var(--radius-md)';
        card.style.border = '1px solid var(--border-subtle)';
        card.style.background = 'var(--bg-card)';
    });
});
