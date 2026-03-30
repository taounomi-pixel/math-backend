import React, { useState, useRef } from 'react';
import { Upload, X, Loader2 } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const UploadModal = ({ onClose, onSuccess }) => {
  const { t } = useLanguage();
  const [title, setTitle] = useState('');
  const [file, setFile] = useState(null);
  const [sourceFile, setSourceFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
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

  const handleSourceChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      if (selected.name.endsWith('.py')) {
        setSourceFile(selected);
        setError('');
      } else {
        setSourceFile(null);
        setError(t('errInvalidSource'));
      }
    }
  };

  const handleUpload = (e) => {
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
    setUploadProgress(0);
    setError('');

    const formData = new FormData();
    formData.append('title', title);
    formData.append('file', file);
    if (sourceFile) {
      console.log("Appending source_file:", sourceFile.name, sourceFile.size);
      formData.append('source_file', sourceFile);
    } else {
      console.log("No source_file selected.");
    }
    
    // Log all keys in FormData for debugging
    for (var pair of formData.entries()) {
      console.log('FormData:', pair[0], pair[1]);
    }

    const apiUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`;
    
    // Using XMLHttpRequest for progress tracking
    const xhr = new XMLHttpRequest();
    
    xhr.open('POST', `${apiUrl}/videos`, true);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    // Track upload progress
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setUploadProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onSuccess && onSuccess();
        onClose();
      } else {
        try {
          const response = JSON.parse(xhr.responseText);
          setError(response.detail || t('errUploadFail'));
        } catch (e) {
          setError(t('errUploadFail'));
        } finally {
          setIsUploading(false);
        }
      }
    };

    xhr.onerror = () => {
      setError(t('errUploadFail'));
      setIsUploading(false);
    };

    xhr.send(formData);
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
                padding: '24px 32px',
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
              <Upload size={24} style={{ color: 'var(--primary-color)', margin: '0 auto 8px auto' }} />
              <div style={{ color: 'var(--text-primary)', fontWeight: '500', fontSize: '14px' }}>
                {file ? file.name : t("selectFileHint")}
              </div>
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '32px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>{t('manimSource')}</label>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <input 
                type="file" 
                accept=".py" 
                onChange={handleSourceChange}
                style={{ display: 'none' }}
                id="source-upload"
                disabled={isUploading}
              />
              <label 
                htmlFor="source-upload"
                className="btn-ghost"
                style={{ 
                  cursor: 'pointer', 
                  flex: '0 0 auto', 
                  padding: '8px 16px', 
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              >
                {t('sourceFileHint')}
              </label>
              <span style={{ fontSize: '14px', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {sourceFile ? sourceFile.name : ''}
              </span>
            </div>
          </div>
          
          <button 
            type="submit" 
            className="btn-primary" 
            style={{ 
              width: '100%', 
              padding: '12px', 
              fontSize: '16px', 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center', 
              gap: '8px',
              position: 'relative',
              overflow: 'hidden'
            }}
            disabled={isUploading}
          >
            {isUploading ? (
              <span style={{ display: 'flex', alignItems: 'center', zIndex: 2 }}>
                <Loader2 size={20} className="spinning" style={{ marginRight: '8px' }} /> 
                {uploadProgress}% {t('btnUploading')}
              </span>
            ) : (
              t('btnUpload')
            )}
            
            {/* Background progress fill */}
            {isUploading && (
              <div 
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  height: '100%',
                  width: `${uploadProgress}%`,
                  background: 'rgba(255, 255, 255, 0.2)',
                  transition: 'width 0.3s ease-out',
                  zIndex: 1
                }}
              />
            )}
          </button>

          {/* Detailed progress bar below button */}
          {isUploading && (
            <div style={{ marginTop: '16px' }}>
              <div style={{ 
                height: '6px', 
                width: '100%', 
                background: 'var(--bg-tertiary)', 
                borderRadius: '3px',
                overflow: 'hidden',
                border: '1px solid var(--border-color)'
              }}>
                <div style={{ 
                  height: '100%', 
                  width: `${uploadProgress}%`, 
                  background: 'var(--accent-primary)',
                  boxShadow: '0 0 10px var(--accent-primary)',
                  transition: 'width 0.3s ease-out'
                }} />
              </div>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                marginTop: '8px', 
                fontSize: '12px', 
                color: 'var(--text-secondary)' 
              }}>
                <span>{uploadProgress < 100 ? t('btnUploading') : 'Processing...'}</span>
                <span>{uploadProgress}%</span>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default UploadModal;
