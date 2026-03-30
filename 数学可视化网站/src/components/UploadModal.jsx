import React, { useState, useRef } from 'react';
import { Upload, X, Loader2 } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const UploadModal = ({ onClose, onSuccess }) => {
  const { t } = useLanguage();
  const [title, setTitle] = useState('');
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.type === 'video/mp4') {
      setFile(selected);
      setError('');
    } else {
      setFile(null);
      setError(t('errInvalidFile'));
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!title.trim() || !file) {
      setError(t('errFieldsRequired'));
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError(t('errLoginRequired'));
      return;
    }

    setIsUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('file', file);

      const apiUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`;
      const response = await fetch(`${apiUrl}/videos`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || t('errUploadFail'));
      }

      onSuccess && onSuccess();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
      {/* Set a high z-index to ensure it sits above the header */}
      <div 
        className="modal-content" 
        onClick={e => e.stopPropagation()}
        style={{ width: '400px', maxWidth: '90%', padding: '24px' }}
      >
        <button className="modal-close" onClick={onClose}>
          <X size={24} />
        </button>
        
        <h2 style={{ marginBottom: '24px', color: 'var(--text-primary)' }}>{t('uploadVideo')}</h2>
        
        {error && <div className="error-message" style={{ marginBottom: '16px', color: '#EF4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: '8px', fontSize: '14px' }}>{error}</div>}
        
        <form onSubmit={handleUpload}>
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>{t('title')}</label>
            <input 
              type="text" 
              className="form-input" 
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('titlePlaceholder')}
              disabled={isUploading}
            />
          </div>
          
          <div className="form-group" style={{ marginBottom: '32px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>{t('videoFile')}</label>
            
            <div 
              className="dropzone" 
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '2px dashed var(--border-color)',
                borderRadius: '8px',
                padding: '32px',
                textAlign: 'center',
                cursor: 'pointer',
                background: 'var(--bg-secondary)',
                transition: 'all 0.2s ease',
              }}
            >
              <input 
                type="file" 
                accept="video/mp4" 
                ref={fileInputRef} 
                onChange={handleFileChange} 
                style={{ display: 'none' }} 
                disabled={isUploading}
              />
              <Upload size={32} style={{ color: 'var(--primary-color)', margin: '0 auto 12px auto' }} />
              <div style={{ color: 'var(--text-primary)', fontWeight: '500' }}>
                {file ? file.name : t("selectFileHint")}
              </div>
            </div>
          </div>
          
          <button 
            type="submit" 
            className="btn-primary" 
            style={{ width: '100%', padding: '12px', fontSize: '16px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
            disabled={isUploading}
          >
            {isUploading ? (
              <span style={{ display: 'flex', alignItems: 'center' }}><Loader2 size={20} className="spinning" style={{ marginRight: '8px' }} /> {t('btnUploading')}</span>
            ) : (
              t('btnUpload')
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default UploadModal;
