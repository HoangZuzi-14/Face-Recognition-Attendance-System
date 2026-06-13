import React from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { LogOut, LayoutDashboard, CalendarRange, UserCheck, Play, History, FileSpreadsheet, Settings as SettingsIcon } from 'lucide-react';

export const AppShell: React.FC = () => {
  const { user, logout, classes, selectedClassId, setSelectedClassId } = useApp();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-shell">
      {/* Sidebar bên trái */}
      <aside className="app-sidebar">
        <Link to="/dashboard" className="brand">
          <span className="brand-mark">✣</span> <span>ZuzoNKT Attendance</span>
        </Link>

        {/* Menu điều hướng dọc */}
        <nav className="main-nav">
          <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </NavLink>
          <NavLink to="/classes" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <CalendarRange size={18} />
            <span>Lớp & Danh sách</span>
          </NavLink>
          <NavLink to="/enrollment" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <UserCheck size={18} />
            <span>Đăng ký khuôn mặt</span>
          </NavLink>
          <NavLink to="/live" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Play size={18} />
            <span>Live Attendance</span>
          </NavLink>
          <NavLink to="/events" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <History size={18} />
            <span>Nhật ký nhận diện</span>
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <FileSpreadsheet size={18} />
            <span>Báo cáo</span>
          </NavLink>
          {user?.role === 'admin' && (
            <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <SettingsIcon size={18} />
              <span>Hệ thống</span>
            </NavLink>
          )}
        </nav>

        {/* Phần chân Sidebar chứa thông tin User & Đăng xuất */}
        <div className="sidebar-footer" style={{ borderTop: '1px solid var(--border)', paddingTop: '1.25rem', marginTop: 'auto' }}>
          {user && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>{user.username}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>
                  {user.role}
                </div>
              </div>
              <button 
                onClick={handleLogout} 
                className="btn btn-danger" 
                style={{ width: '100%', height: '38px', fontSize: '0.85rem', padding: '0 0.75rem', gap: '0.35rem' }} 
                title="Đăng xuất"
              >
                <LogOut size={14} />
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Vùng chính bên phải */}
      <div className="app-main-area">
        {/* Header ngang phía trên */}
        <header className="app-header">
          {/* Breadcrumb / Tiêu đề động */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>Cổng thông tin</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>/</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {user?.role} Portal
            </span>
          </div>

          {/* Header Right: Bộ chọn lớp học toàn cục */}
          <div className="header-right">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Lớp học:</span>
              <select
                value={selectedClassId || ''}
                onChange={(e) => setSelectedClassId(e.target.value ? Number(e.target.value) : null)}
                className="form-input"
                style={{ width: '220px', height: '36px', fontSize: '0.85rem', padding: '0 0.5rem' }}
              >
                <option value="">-- Chọn lớp học --</option>
                {classes.map((cls) => (
                  <option key={cls.id} value={cls.id}>
                    {cls.class_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </header>

        {/* Nội dung trang */}
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
