import React, { useState, useEffect } from 'react';
import { Search, Globe, ChevronDown, User, Menu, X, LogOut, Upload } from 'lucide-react';
import UploadModal from './UploadModal';
import { useLanguage } from '../contexts/LanguageContext';

const Header = ({ searchQuery, setSearchQuery }) => {
  const { lang, setLang, t } = useLanguage();
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState(false);

  // Auth States
  const [currentUser, setCurrentUser] = useState(null);
  const [authModal, setAuthModal] = useState(null); // 'login' | 'register' | null
  const [authForm, setAuthForm] = useState({ username: '', password: '' });
  const [authError, setAuthError] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Auto-login check on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const storedUsername = localStorage.getItem('username');
    if (token && storedUsername) {
      setCurrentUser({ username: storedUsername });
    }
  }, []);

  // Auto-close mobile nav on resize
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768 && isMobileNavOpen) {
        setIsMobileNavOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isMobileNavOpen]);

  // Auth Functions
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    
    try {
      if (authModal === 'register') {
        // Since FastAPI expects user_in as a top level payload and password as query/separate param
        // Wait, the backend expects: @app.post("/api/register") def register_user(user_in: UserBase, password: str)
        // Actually FastAPI uses Query params if missing model wrapper. To make it standard JSON, we must adapt to how we scaffolded it.
        // Actually I defined it as JSON body but FastAPI splits the arguments. It's safer to hit login right after or adjust the POST body:
        const apiUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`;
        const url = new URL(`${apiUrl}/register`);
        url.searchParams.append('password', authForm.password);

        const res = await fetch(url.toString(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: authForm.username }) // This maps to UserBase
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || t('regFail'));
        }
        // Auto switch to login
        setAuthModal('login');
        setAuthError(t('regSuccess'));
      } else if (authModal === 'login') {
        const formData = new URLSearchParams();
        formData.append('username', authForm.username);
        formData.append('password', authForm.password);
        
        const apiUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`;
        const res = await fetch(`${apiUrl}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData.toString()
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || t('loginFail'));
        }
        const data = await res.json();
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('username', authForm.username);
        setCurrentUser({ username: authForm.username });
        setAuthModal(null);
        setAuthForm({ username: '', password: '' });
      }
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    setCurrentUser(null);
  };

  return (
    <>
      <header className="header">
        <div className="header-inner container">
          <a href="/" className="logo">
            <div className="logo-icon-wrap">
              <svg viewBox="0 0 24 24" className="logo-icon" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="4 20 4 4 20 4"></polyline>
                <path d="M4 20 Q12 16 12 12 T20 4"></path>
              </svg>
            </div>
            <span className="logo-text">MathVis</span>
          </a>

          <div className="header-search">
            <label htmlFor="search-input" className="visually-hidden">Search for theorems</label>
            <Search className="search-icon" size={18} />
            <input 
              type="text" 
              id="search-input" 
              placeholder={t('searchPlaceholder')}
              autoComplete="off" 
              value={searchQuery || ''}
              onChange={(e) => setSearchQuery && setSearchQuery(e.target.value)}
            />
            <div className="search-kbd">
              <kbd>Ctrl</kbd>+<kbd>K</kbd>
            </div>
          </div>

          <nav className="header-actions">
            <div className="dropdown" id="lang-switcher">
              <button 
                className="dropdown-trigger btn-ghost" 
                aria-haspopup="true" 
                aria-expanded={isLangDropdownOpen}
                onClick={() => setIsLangDropdownOpen(!isLangDropdownOpen)}
              >
                <Globe size={18} />
                <span className="current-lang">{lang.toUpperCase()}</span>
                <ChevronDown size={16} className="dropdown-arrow" />
              </button>
              <div className={`dropdown-menu ${isLangDropdownOpen ? 'show' : ''}`}>
                <button 
                  className={`dropdown-item ${lang === 'en' ? 'active' : ''}`} 
                  onClick={() => { setLang('en'); setIsLangDropdownOpen(false); }}
                >
                  {t('langEN')}
                </button>
                <button 
                  className={`dropdown-item ${lang === 'zh' ? 'active' : ''}`} 
                  onClick={() => { setLang('zh'); setIsLangDropdownOpen(false); }}
                >
                  {t('langZH')}
                </button>
              </div>
            </div>
            
            {/* Dynamic Sign In / User Profile */}
            {currentUser ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button 
                  className="btn-ghost" 
                  onClick={() => setShowUploadModal(true)} 
                  title={t('upload')} 
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}
                >
                  <Upload size={16} /> <span style={{ fontSize: '14px', fontWeight: 500 }}>{t('upload')}</span>
                </button>
                <div style={{ 
                  width: '32px', height: '32px', borderRadius: '50%', 
                  background: 'var(--primary)', color: 'white', 
                  display: 'flex', alignItems: 'center', justifyContent: 'center', 
                  fontWeight: 'bold', fontSize: '14px', flexShrink: 0
                }}>
                  {currentUser.username[0].toUpperCase()}
                </div>
                <span style={{ fontWeight: 500, fontSize: '14px' }}>{currentUser.username}</span>
                <button className="btn-ghost" onClick={handleLogout} title={t('logout')} style={{ padding: '8px' }}>
                  <LogOut size={16} />
                </button>
              </div>
            ) : (
              <button className="btn-primary sign-in-btn" onClick={() => setAuthModal('login')}>
                <User size={16} />
                <span>{t('signIn')}</span>
              </button>
            )}
          </nav>
          
          <button 
            className={`mobile-menu-btn ${isMobileNavOpen ? 'active' : ''}`} 
            id="mobile-menu-btn" 
            aria-label="Toggle Navigation"
            onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}
          >
            <Menu size={24} />
          </button>
        </div>

        <div className={`mobile-nav ${isMobileNavOpen ? 'open' : ''}`} id="mobile-nav">
          <div className="container mobile-nav-inner">
            <div className="header-search mobile-search">
              <Search className="search-icon" size={18} />
              <input 
                type="text" 
                placeholder={t('searchPlaceholder')} 
                autoComplete="off"
                value={searchQuery || ''}
                onChange={(e) => setSearchQuery && setSearchQuery(e.target.value)}
              />
            </div>
            <div className="mobile-actions">
              <button className="btn-outline mobile-nav-btn" onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}>
                <Globe size={16} /> {t('language')}: {lang.toUpperCase()}
              </button>
              {currentUser ? (
                <button className="btn-outline mobile-nav-btn" onClick={handleLogout} style={{ color: 'var(--error-color)' }}>
                  <LogOut size={16} /> {t('logout')} ({currentUser.username})
                </button>
              ) : (
                <button className="btn-primary sign-in-btn mobile-nav-btn" onClick={() => setAuthModal('login')}>
                  <User size={16} /> {t('signIn')}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Auth Modal UI */}
      {authModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            background: 'white', padding: '32px', borderRadius: '16px', 
            width: '90%', maxWidth: '400px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
              <h2 style={{ fontSize: '24px', margin: 0, color: 'var(--text-primary)' }}>
                {authModal === 'login' ? t('loginTitle') : t('registerTitle')}
              </h2>
              <button 
                onClick={() => setAuthModal(null)} 
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
              >
                <X size={24} />
              </button>
            </div>
            
            {authError && (
              <div style={{ padding: '12px', background: '#fee2e2', color: '#dc2626', borderRadius: '8px', marginBottom: '16px', fontSize: '14px' }}>
                {authError}
              </div>
            )}
            
            <form onSubmit={handleAuthSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500, fontSize: '14px' }}>{t('username')}</label>
                <input 
                  type="text" 
                  value={authForm.username}
                  onChange={e => setAuthForm({...authForm, username: e.target.value})}
                  required
                  autoFocus
                  style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', outline: 'none' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500, fontSize: '14px' }}>{t('password')}</label>
                <input 
                  type="password" 
                  value={authForm.password}
                  onChange={e => setAuthForm({...authForm, password: e.target.value})}
                  required
                  style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', outline: 'none' }}
                />
              </div>
              <button type="submit" className="btn-primary btn-lg" style={{ marginTop: '8px', width: '100%', justifyContent: 'center' }}>
                {authModal === 'login' ? t('continueBtn') : t('createAccountBtn')}
              </button>
            </form>
            
            <div style={{ marginTop: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '14px' }}>
              {authModal === 'login' ? t('noAccount') : t('hasAccount')}
              <button 
                type="button"
                onClick={() => { setAuthModal(authModal === 'login' ? 'register' : 'login'); setAuthError(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontWeight: 500, padding: 0 }}
              >
                {authModal === 'login' ? t('signUpLink') : t('signInLink')}
              </button>
            </div>
          </div>
        </div>
      )}

      {showUploadModal && (
        <UploadModal 
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            window.dispatchEvent(new Event('videoUploaded'));
          }}
        />
      )}
    </>
  );
};

export default Header;
