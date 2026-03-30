import React, { useState, useEffect } from 'react';
import { PlayCircle, Bookmark, Play, Heart, Loader2, Trash2, Code } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const TheoremCard = ({ searchQuery = "" }) => {
  const { t } = useLanguage();
  const [videos, setVideos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchVideos = async () => {
    setIsLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`;
      const response = await fetch(`${apiUrl}/videos`);
      if (!response.ok) throw new Error('Failed to fetch videos');
      const data = await response.json();
      setVideos(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
    
    // Listen for upload success events triggered by Header > UploadModal
    window.addEventListener('videoUploaded', fetchVideos);
    return () => {
      window.removeEventListener('videoUploaded', fetchVideos);
    };
  }, []);

  const currentUserId = localStorage.getItem('user_id') ? parseInt(localStorage.getItem('user_id'), 10) : null;
  const currentUsername = localStorage.getItem('username');

  const handleDelete = async (videoId) => {
    if (!window.confirm(t('deleteConfirm'))) return;

    const token = localStorage.getItem('access_token');
    try {
      const apiUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`;
      const response = await fetch(`${apiUrl}/videos/${videoId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error(t('errDeleteFail'));

      // Remove from state
      setVideos(prev => prev.filter(v => v.id !== videoId));
      alert(t('deleteSuccess'));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleLike = async (videoId) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      alert(t('loginToLike'));
      return;
    }
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`;
      const res = await fetch(`${apiUrl}/videos/${videoId}/like`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error('Action failed');
      const data = await res.json();
      
      // Update UI optimistically
      setVideos(prev => prev.map(v => 
        v.id === videoId 
          ? { ...v, like_count: data.like_count, _liked: data.action === 'liked' } 
          : v
      ));
    } catch (err) {
      console.error(err);
    }
  };

  if (isLoading && videos.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '64px' }}>
        <Loader2 className="spinning" size={32} color="var(--primary)" />
      </div>
    );
  }

  if (error) {
    return <div className="error-message" style={{ margin: '32px' }}>{error}</div>;
  }

  // Fallback to static if no database entries yet
  if (videos.length === 0) {
    return (
      <div style={{ 
        textAlign: 'center', padding: '64px', margin: '32px 0',
        background: 'var(--bg-secondary)', borderRadius: '16px', border: '1px dashed var(--border-color)'
      }}>
        <h3 style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>{t('noRecords')}</h3>
        <p style={{ color: 'var(--text-secondary)' }}>{t('loginToUploadDesc')}</p>
      </div>
    );
  }

  // Define Filter Logic: title, uploader_username, and tags
  const lowerQuery = searchQuery.toLowerCase().trim();
  const filteredVideos = videos.filter(video => {
    if (!lowerQuery) return true;
    
    const titleMatch = (video.title || "").toLowerCase().includes(lowerQuery);
    const uploaderMatch = (video.uploader_username || "").toLowerCase().includes(lowerQuery);
    
    // Check tags if they exist. (Simulating backend tags support for flexibility)
    const tags = video.tags || [];
    const tagsMatch = tags.some(tag => tag.toLowerCase().includes(lowerQuery));

    return titleMatch || uploaderMatch || tagsMatch;
  });

  if (filteredVideos.length === 0 && videos.length > 0) {
    return (
      <div style={{ textAlign: 'center', margin: '32px 0', padding: '64px', background: 'var(--bg-secondary)', borderRadius: '16px' }}>
        <h3 style={{ color: 'var(--text-primary)' }}>{t('noResultsFor')} "{searchQuery}"</h3>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '48px', margin: '24px 0' }}>
      {filteredVideos.map(video => (
        <VideoItem 
          key={video.id} 
          video={video} 
          handleLike={handleLike} 
          handleDelete={handleDelete}
          isOwner={currentUserId === video.uploader_id || (currentUsername && currentUsername === video.uploader_username)}
          t={t} 
        />
      ))}
    </div>
  );
};

const VideoItem = ({ video, handleLike, handleDelete, isOwner, t }) => {
  return (
    <section className="hero-section" style={{ minHeight: 'auto', padding: '32px', gap: '32px' }}>
      <div className="hero-content">
        <span className="badge">{t('uploadedBy')} @{video.uploader_username}</span>
        <h2 className="hero-title" style={{ fontSize: '32px', margin: '16px 0' }}>{video.title}</h2>
        <p className="hero-desc" style={{ fontSize: '15px' }}>
          {t('uploadedOn')} {new Date(video.upload_time).toLocaleDateString()}
        </p>
        <div className="hero-actions" style={{ marginTop: '24px' }}>
          <button 
            className={`btn-primary ${video._liked ? 'liked' : ''}`} 
            onClick={() => handleLike(video.id)} 
            style={video._liked ? { 
              display: 'flex', gap: '8px', alignItems: 'center',
              backgroundColor: '#ec4899',
              borderColor: '#ec4899',
              transition: 'background 0.2s'
            } : {
              display: 'flex', gap: '8px', alignItems: 'center',
              transition: 'background 0.2s'
            }}
          >
            <Heart size={20} fill={video._liked ? "currentColor" : "none"} /> 
            {video.like_count} {t('likes')}
          </button>
          
          {video.manim_source_url && (
            <button 
              className="btn-ghost" 
              onClick={() => window.open(video.manim_source_url, '_blank')}
              style={{ 
                display: 'flex', gap: '8px', alignItems: 'center', 
                padding: '8px 16px', border: '1px solid var(--border-color)', 
                borderRadius: '8px', color: 'var(--text-primary)' 
              }}
            >
              <Code size={18} />
              {t('viewCode')}
            </button>
          )}
          
          {isOwner && (
            <button 
              className="btn-ghost" 
              onClick={() => handleDelete(video.id)}
              style={{ 
                display: 'flex', gap: '8px', alignItems: 'center', 
                color: '#ef4444', padding: '8px 16px',
                border: '1px solid #fecaca', borderRadius: '8px'
              }}
            >
              <Trash2 size={18} />
              {t('btnDelete')}
            </button>
          )}
        </div>
      </div>
      <div className="hero-visual" style={{ flex: '1 1 50%' }}>
        <div style={{ borderRadius: '16px', overflow: 'hidden', background: '#000', width: '100%', aspectRatio: '16/9', boxShadow: 'var(--shadow-md)' }}>
          <video 
            src={video.video_url.startsWith('http') ? video.video_url : `${import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace('/api', '') : `http://${window.location.hostname}:8000`}${video.video_url}`}
            controls 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            preload="metadata"
          >
            Your browser does not support HTML video.
          </video>
        </div>
      </div>
    </section>
  );
};

export default TheoremCard;
