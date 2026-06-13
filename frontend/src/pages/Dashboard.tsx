import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Users, Database, RefreshCw, ArrowRight, Play, UserPlus } from 'lucide-react';

interface PreflightData {
  active_identity_count: number;
  face_db_status: string;
  face_db_path: string;
  sqlite_status: string;
  sqlite_db_path: string;
  liveness_enabled: boolean;
}

interface SummaryData {
  roster_count: number;
  registered_count: number;
  has_roster: boolean;
}

interface AttendanceTodayData {
  rows: any[];
  summary: {
    present: number;
    late: number;
    absent: number;
    unknown: number;
    total: number;
  };
}

export const Dashboard: React.FC = () => {
  const { selectedClassId, fetchWithAuth } = useApp();
  const navigate = useNavigate();
  const [preflight, setPreflight] = useState<PreflightData | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [attendance, setAttendance] = useState<AttendanceTodayData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    if (!selectedClassId) return;
    setIsLoading(true);
    setError(null);
    try {
      // Gọi song song 3 API
      const [preflightData, summaryData, attendanceData] = await Promise.all([
        fetchWithAuth(`/api/classes/${selectedClassId}/camera/preflight`),
        fetchWithAuth(`/api/classes/${selectedClassId}/summary`),
        fetchWithAuth(`/api/classes/${selectedClassId}/attendance/today?deadline_hour=8&deadline_minute=0`)
      ]);

      setPreflight(preflightData);
      setSummary(summaryData);
      setAttendance(attendanceData);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Lỗi không thể tải dữ liệu dashboard.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [selectedClassId]);

  if (!selectedClassId) {
    return (
      <div className="zuzo-card" style={{ minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
        <div>
          <span style={{ fontSize: '3rem', opacity: 0.1, display: 'block', marginBottom: '1rem' }}>🎓</span>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 500, marginBottom: '0.5rem' }}>Chưa chọn lớp học</h2>
          <p style={{ color: 'var(--text-muted)' }}>Vui lòng chọn lớp học ở thanh điều hướng phía trên để xem tổng quan.</p>
        </div>
      </div>
    );
  }

  const isReadyToRun = preflight && preflight.active_identity_count > 0 && preflight.face_db_status === 'available' && preflight.sqlite_status === 'available';

  return (
    <div>
      {/* Header trang */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 className="font-display" style={{ fontSize: '2.5rem', fontWeight: 500 }}>Bảng Tổng Quan</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Theo dõi tình trạng sẵn sàng của lớp học và kết quả điểm danh nhanh.</p>
        </div>
        <button onClick={fetchDashboardData} className="btn" style={{ marginLeft: 'auto', gap: '0.35rem' }} disabled={isLoading}>
          <RefreshCw size={16} className={isLoading ? 'spin' : ''} />
          Làm mới
        </button>
      </div>

      {error && (
        <div className="zuzo-card" style={{ backgroundColor: 'var(--danger-bg)', border: '1px solid rgba(197, 34, 31, 0.2)', color: 'var(--danger)', padding: '1rem', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="zuzo-card" style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: 0 }}>
          <div style={{ backgroundColor: 'var(--surface-raised)', color: 'var(--primary)', padding: '1rem', borderRadius: '12px' }}>
            <Users size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tổng sinh viên</div>
            <div className="mono" style={{ fontSize: '1.8rem', fontWeight: 700 }}>
              {isLoading ? '...' : summary?.roster_count ?? 0}
            </div>
          </div>
        </div>

        <div className="zuzo-card" style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: 0 }}>
          <div style={{ backgroundColor: 'var(--success-bg)', color: 'var(--success)', padding: '1rem', borderRadius: '12px' }}>
            <Database size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Khuôn mặt đã enroll</div>
            <div className="mono" style={{ fontSize: '1.8rem', fontWeight: 700 }}>
              {isLoading ? '...' : summary?.registered_count ?? 0}
            </div>
          </div>
        </div>

        <div className="zuzo-card" style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: 0 }}>
          <div style={{ backgroundColor: 'var(--warning-bg)', color: 'var(--warning)', padding: '1rem', borderRadius: '12px' }}>
            <UserPlus size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Thiếu khuôn mặt</div>
            <div className="mono" style={{ fontSize: '1.8rem', fontWeight: 700 }}>
              {isLoading ? '...' : (summary ? (summary.roster_count - summary.registered_count) : 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="grid-2">
        {/* Cột trái: Kết quả điểm danh hôm nay */}
        <div className="zuzo-card">
          <h3 className="zuzo-card-title">Điểm Danh Hôm Nay</h3>
          {isLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>Đang tải...</div>
          ) : attendance ? (
            <div>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'space-around', padding: '1.5rem 0', borderBottom: '1px solid var(--border)' }}>
                <div style={{ textAlign: 'center' }}>
                  <span className="badge badge-present" style={{ fontSize: '1.2rem', padding: '0.5rem 1rem', height: 'auto' }}>
                    {attendance.summary.present}
                  </span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 600 }}>Có mặt</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <span className="badge badge-late" style={{ fontSize: '1.2rem', padding: '0.5rem 1rem', height: 'auto' }}>
                    {attendance.summary.late}
                  </span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 600 }}>Đi muộn</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <span className="badge badge-absent" style={{ fontSize: '1.2rem', padding: '0.5rem 1rem', height: 'auto' }}>
                    {attendance.summary.absent}
                  </span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 600 }}>Vắng mặt</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <span className="badge badge-unknown" style={{ fontSize: '1.2rem', padding: '0.5rem 1rem', height: 'auto' }}>
                    {attendance.summary.unknown}
                  </span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 600 }}>Chưa đăng ký</div>
                </div>
              </div>

              {/* Bảng xem trước danh sách vắng/thiếu mặt */}
              <div style={{ marginTop: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Danh sách điểm danh nhanh</span>
                  <button onClick={() => navigate('/reports')} className="btn" style={{ height: '30px', padding: '0 0.5rem', fontSize: '0.75rem', gap: '0.25rem' }}>
                    Xem chi tiết <ArrowRight size={12} />
                  </button>
                </div>
                
                <div className="table-container" style={{ maxHeight: '200px' }}>
                  <table className="zuzo-table">
                    <thead>
                      <tr>
                        <th>MSSV</th>
                        <th>Họ tên</th>
                        <th style={{ textAlign: 'right' }}>Trạng thái</th>
                      </tr>
                    </thead>
                    <tbody>
                      {attendance.rows.slice(0, 5).map((row, idx) => (
                        <tr key={idx}>
                          <td className="mono">{row.mssv}</td>
                          <td>{row.full_name}</td>
                          <td style={{ textAlign: 'right' }}>
                            <span className={`badge badge-${row.status.toLowerCase()}`}>
                              {row.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                      {attendance.rows.length === 0 && (
                        <tr>
                          <td colSpan={3} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Chưa có dữ liệu điểm danh.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>Chưa có dữ liệu điểm danh.</div>
          )}
        </div>

        {/* Cột phải: Trạng thái sẵn sàng (Preflight) */}
        <div className="zuzo-card">
          <h3 className="zuzo-card-title">Tình Trạng Sẵn Sàng (Preflight)</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '2rem' }}>
            <div className="preflight-item">
              <span style={{ fontSize: '0.875rem' }}>Cơ sở dữ liệu SQLite:</span>
              <div className="preflight-status">
                <span className={`status-indicator ${preflight?.sqlite_status === 'available' ? 'ok' : 'error'}`} />
                <span className="mono">{preflight?.sqlite_status === 'available' ? 'KẾT NỐI TỐT' : 'KHÔNG KHẢ DỤNG'}</span>
              </div>
            </div>

            <div className="preflight-item">
              <span style={{ fontSize: '0.875rem' }}>Face DB Pickle (`db.pkl`):</span>
              <div className="preflight-status">
                <span className={`status-indicator ${preflight?.face_db_status === 'available' ? 'ok' : 'error'}`} />
                <span className="mono">{preflight?.face_db_status === 'available' ? 'ĐÃ TẢI' : 'MẤT KẾT NỐI'}</span>
              </div>
            </div>

            <div className="preflight-item">
              <span style={{ fontSize: '0.875rem' }}>Số sinh viên có mặt hoạt động:</span>
              <div className="preflight-status">
                <span className={`status-indicator ${preflight && preflight.active_identity_count > 0 ? 'ok' : 'error'}`} />
                <span className="mono">{preflight?.active_identity_count ?? 0} khuôn mặt</span>
              </div>
            </div>

            <div className="preflight-item">
              <span style={{ fontSize: '0.875rem' }}>Hệ thống chống giả mạo (Liveness):</span>
              <div className="preflight-status">
                <span className={`status-indicator ${preflight?.liveness_enabled ? 'ok' : 'warning'}`} />
                <span className="mono">{preflight?.liveness_enabled ? 'ĐANG BẬT (PAD)' : 'BỊ TẮT'}</span>
              </div>
            </div>
          </div>

          {/* Quick Actions Panel */}
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Lối tắt nhanh</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <button
                onClick={() => navigate('/live')}
                className="btn btn-primary"
                style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem' }}
                disabled={!isReadyToRun}
              >
                <Play size={16} />
                Điểm danh trực tiếp (Live Camera)
              </button>
              
              <button
                onClick={() => navigate('/enrollment')}
                className="btn"
                style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem' }}
              >
                <UserPlus size={16} />
                Đăng ký khuôn mặt mới (Enroll)
              </button>
            </div>
            {!isReadyToRun && preflight && (
              <p style={{ color: 'var(--danger)', fontSize: '0.75rem', marginTop: '0.5rem', fontWeight: 500 }}>
                * Hệ thống chưa đủ điều kiện để điểm danh (thiếu Roster hoặc khuôn mặt). Vui lòng cấu hình ở Lớp & Danh sách hoặc Đăng ký khuôn mặt trước.
              </p>
            )}
          </div>
        </div>
      </div>
      
      {/* CSS Spin effect */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
};
