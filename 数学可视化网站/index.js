/**
 * MathVis Platform Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Lucide Icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  // 2. Language Switcher Dropdown Logic
  const langSwitcher = document.getElementById('lang-switcher');
  if (langSwitcher) {
    const trigger = langSwitcher.querySelector('.dropdown-trigger');
    const menu = langSwitcher.querySelector('.dropdown-menu');
    const currentLangText = langSwitcher.querySelector('.current-lang');
    const items = langSwitcher.querySelectorAll('.dropdown-item');

    // Toggle Menu
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = trigger.getAttribute('aria-expanded') === 'true';
      trigger.setAttribute('aria-expanded', !isExpanded);
      menu.classList.toggle('show');
    });

    // Handle Item Selection
    items.forEach(item => {
      item.addEventListener('click', () => {
        // Update active class
        items.forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        
        // Update label (extract the 'EN', 'ZH', etc. from text)
        const langCode = item.getAttribute('data-lang').toUpperCase();
        currentLangText.textContent = langCode;

        // Close menu
        trigger.setAttribute('aria-expanded', 'false');
        menu.classList.remove('show');
        
        // Mock notification for changing language
        console.log(`Language switched to: ${langCode}`);
      });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!langSwitcher.contains(e.target)) {
        trigger.setAttribute('aria-expanded', 'false');
        menu.classList.remove('show');
      }
    });
  }

  // 3. Search Shortcut (Ctrl+K or Cmd+K)
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
      }
    });

    // Optional: Log search events
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value;
        if (query.trim()) {
           console.log(`Searching for theorems matching: ${query}`);
           alert(`Searching for: ${query}`);
        }
      }
    });
  }

  // 4. Topic Filter Logic
  const topicBtns = document.querySelectorAll('.topic-btn');
  topicBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      topicBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // In a real app, this would filter the video grid below
      console.log(`Filtering by topic: ${btn.textContent}`);
    });
  });

  // 5. Sign In Button Mock Add Event
  const signinBtns = document.querySelectorAll('.sign-in-btn');
  signinBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      alert("Sign In modal would open here.");
    });
  });

  // 6. Mobile Menu Toggle
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const mobileNav = document.getElementById('mobile-nav');
  if (mobileMenuBtn && mobileNav) {
    mobileMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      mobileNav.classList.toggle('open');
      mobileMenuBtn.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!mobileNav.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
        mobileNav.classList.remove('open');
        mobileMenuBtn.classList.remove('active');
      }
    });

    // 7. Auto close mobile menu when window is resized back to desktop view
    window.addEventListener('resize', () => {
      if (window.innerWidth > 768 && mobileNav.classList.contains('open')) {
        mobileNav.classList.remove('open');
        mobileMenuBtn.classList.remove('active');
      }
    });

    // Refresh icons inside mobile nav dynamically created
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }
});
