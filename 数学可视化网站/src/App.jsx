import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { LanguageProvider, useLanguage } from './contexts/LanguageContext';

// Import Components
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import TheoremCard from './components/TheoremCard';

// Main Layout Wrapper
const Layout = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const { t } = useLanguage();

  return (
    <>
      <Header searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
      <main className="main-content container">
        <Sidebar />
        
        <div className="page-content" style={{ marginTop: '24px', animation: 'fadeIn 0.3s ease' }}>
          <Routes>
            <Route path="/" element={<TheoremCard searchQuery={searchQuery} />} />
            <Route path="/calculus" element={<PlaceholderPage title={t("Calculus")} description={t("descCalculus")} />} />
            <Route path="/geometry" element={<PlaceholderPage title={t("Geometry")} description={t("descGeometry")} />} />
            <Route path="/linear-algebra" element={<PlaceholderPage title={t("Linear Algebra")} description={t("descLinear")} />} />
            <Route path="/number-theory" element={<PlaceholderPage title={t("Number Theory")} description={t("descNumber")} />} />
            <Route path="/topology" element={<PlaceholderPage title={t("Topology")} description={t("descTopology")} />} />
            <Route path="/probability" element={<PlaceholderPage title={t("Probability")} description={t("descProbability")} />} />
            <Route path="*" element={<PlaceholderPage title={t("titleNotFound")} description={t("descNotFound")} />} />
          </Routes>
        </div>
      </main>
    </>
  );
};

// Generic Placeholder Component
const PlaceholderPage = ({ title, description }) => (
  <div style={{
    padding: '48px 32px',
    background: 'white',
    borderRadius: '16px',
    border: '1px solid var(--border-color)',
    boxShadow: 'var(--shadow-sm)',
    textAlign: 'center'
  }}>
    <h2 style={{ fontSize: '28px', color: 'var(--text-primary)', marginBottom: '16px' }}>{title}</h2>
    <p style={{ color: 'var(--text-secondary)', fontSize: '18px' }}>{description}</p>
  </div>
);

// Main App Router
export default function App() {
  return (
    <LanguageProvider>
      <Router>
        <Layout />
      </Router>
    </LanguageProvider>
  );
}
