import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { KeyRound, User, Lock, AlertCircle } from 'lucide-react';

export const Login: React.FC = () => {
  const { login } = useApp();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Lỗi đăng nhập không mong muốn.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f8fafc' }}>
      {/* Cột trái (Thương hiệu - Phong cách HUST Academic Premium) */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '5rem',
          backgroundColor: '#0a0f1d', /* Dark navy sâu thẳm */
          color: '#ffffff',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <div style={{ position: 'relative', zIndex: 2 }}>
          {/* Logo HUST Cách Điệu */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.5rem' }}>
            <span style={{ 
              color: 'var(--text-inverse)', 
              fontSize: '2.5rem', 
              fontWeight: 900,
              lineHeight: 1,
              textShadow: '0 0 15px rgba(206, 22, 40, 0.4)'
            }}>✣</span>
            <span style={{ 
              fontFamily: 'var(--font-display)', 
              fontSize: '1.25rem', 
              fontWeight: 700, 
              letterSpacing: '0.1em',
              color: '#ffffff',
              borderLeft: '2px solid #ce1628',
              paddingLeft: '0.75rem'
            }}>ZUZONKT ATTENDANCE</span>
          </div>

          <h1 style={{ 
            fontFamily: 'var(--font-display)', 
            fontSize: '3rem', 
            fontWeight: 700, 
            lineHeight: 1.2, 
            marginBottom: '1.5rem',
            background: 'linear-gradient(135deg, #ffffff 60%, #93c5fd 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            Smart Attendance Management System
          </h1>
          <p style={{ fontSize: '1rem', color: '#94a3b8', maxWidth: '500px', fontWeight: 400, lineHeight: 1.6 }}>
            Hệ thống quản lý điểm danh thông minh tích hợp nhận diện khuôn mặt và công nghệ chống giả mạo tiên tiến (Passive Liveness Detection) dành cho trường đại học.
          </p>
        </div>
        
        {/* Background Subtle Grid Pattern & Decorative Glow */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            opacity: 0.04,
            backgroundSize: '30px 30px',
            backgroundImage: 'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)'
          }}
        />
        
        <div
          style={{
            position: 'absolute',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            filter: 'blur(80px)',
            bottom: '-10%',
            right: '-10%',
            zIndex: 1
          }}
        />
      </div>

      {/* Cột phải (Form đăng nhập) */}
      <div
        style={{
          width: '540px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '5rem',
          backgroundColor: '#ffffff',
          borderLeft: '1px solid var(--border)'
        }}
      >
        <div style={{ marginBottom: '2.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Xác thực người dùng
          </span>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 600, marginTop: '0.35rem', color: '#0f172a' }}>
            Chào mừng trở lại
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Nhập tài khoản Admin hoặc Giáo viên của bạn để tiếp tục.
          </p>
        </div>

        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              backgroundColor: 'var(--danger-bg)',
              color: 'var(--danger)',
              padding: '0.85rem 1rem',
              borderRadius: '8px',
              border: '1px solid rgba(206, 22, 40, 0.15)',
              marginBottom: '1.75rem',
              fontSize: '0.85rem'
            }}
          >
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Tên đăng nhập</label>
            <div style={{ position: 'relative' }}>
              <User
                size={18}
                style={{
                  position: 'absolute',
                  left: '14px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)'
                }}
              />
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: '42px' }}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="teacher hoặc admin"
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '2.5rem' }}>
            <label className="form-label">Mật khẩu</label>
            <div style={{ position: 'relative' }}>
              <Lock
                size={18}
                style={{
                  position: 'absolute',
                  left: '14px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)'
                }}
              />
              <input
                type="password"
                className="form-input"
                style={{ paddingLeft: '42px' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu"
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ 
              width: '100%', 
              height: '46px', 
              gap: '0.75rem',
              boxShadow: '0 4px 12px rgba(206, 22, 40, 0.15)'
            }}
            disabled={isLoading}
          >
            <KeyRound size={18} />
            {isLoading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>
      </div>
    </div>
  );
};
