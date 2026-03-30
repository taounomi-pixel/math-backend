import React from 'react';
import { NavLink } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';

const Sidebar = () => {
  const { t } = useLanguage();
  
  const topics = [
    { title: t('All Topics'), path: '/' },
    { title: t('Calculus'), path: '/calculus' },
    { title: t('Geometry'), path: '/geometry' },
    { title: t('Linear Algebra'), path: '/linear-algebra' },
    { title: t('Number Theory'), path: '/number-theory' },
    { title: t('Topology'), path: '/topology' },
    { title: t('Probability'), path: '/probability' },
  ];

  return (
    <div className="topics-filter">
      {topics.map((topic, index) => (
        <NavLink 
          key={index} 
          to={topic.path}
          className={({ isActive }) => `topic-btn ${isActive ? 'active' : ''}`}
          end={topic.path === '/'}
        >
          {topic.title}
        </NavLink>
      ))}
    </div>
  );
};

export default Sidebar;
