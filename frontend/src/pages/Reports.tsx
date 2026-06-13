import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Download, RefreshCw, Calendar, Users, Award, BookOpen } from 'lucide-react';

interface AttendanceRow {
  mssv: string;
  full_name: string;
  time: string;
  status: string;
}

export const Reports: React.FC = () => {
  const { selectedClassId, fetchWithAuth } = useApp();
  const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [summary, setSummary] = useState({ present: 0, late: 0, absent: 0, unknown: 0, total: 0 });
  const [deadlineHour, setDeadlineHour] = useState(8);
  const [deadlineMinute, setDeadlineMinute] = useState(0);
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReportData = async () => {
    if (!selectedClassId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchWithAuth(`/api/classes/${selectedClassId}/attendance/today?deadline_hour=${deadlineHour}&deadline_minute=${deadlineMinute}`);
      setRows(data.rows);
      setSummary(data.summary);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Lỗi không thể tải dữ liệu báo cáo.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReportData();
  }, [selectedClassId, deadlineHour, deadlineMinute]);

  const handleExportCSV = async () => {
    if (!selectedClassId) return;
    try {
      const res = await fetchWithAuth(`/api/classes/${selectedClassId}/attendance/export.csv`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `attendance_report_class_${selectedClassId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      setError('Lỗi xuất tệp tin báo cáo CSV.');
    }
  };

  if (!selectedClassId) {
    return (
      <div className="zuzo-card" style={{ minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
        <div>
          <span style={{ fontSize: '3rem', opacity: 0.1, display: 'block', marginBottom: '1rem' }}>🎓</span>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 500, marginBottom: '0.5rem' }}>Chưa chọn lớp học</h2>
          <p style={{ color: 'var(--text-muted)' }}>Vui lòng chọn lớp học ở thanh điều hướng phía trên để xem báo cáo điểm danh.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header trang */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 className="font-display" style={{ fontSize: '2.5rem', fontWeight: 500 }}>Báo cáo điểm danh (Reports)</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Xuất và tải kết quả điểm danh của lớp học hôm nay.</p>
        </div>
        
        <div style={{ display: 'flex', gap: '0.75rem', marginLeft: 'auto', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginRight: '1rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Mốc đi muộn:</span>
            <input 
              type="number" 
              value={deadlineHour} 
              onChange={(e) => setDeadlineHour(Math.min(23, Math.max(0, parseInt(e.target.value) || 0)))}
              min={0} 
              max={23} 
              style={{ width: '45px', padding: '4px 6px', border: '1px solid var(--border)', borderRadius: '6px', background: 'var(--surface)', color: 'var(--text-primary)', textAlign: 'center', fontSize: '0.85rem' }} 
            />
            <span style={{ color: 'var(--text-muted)' }}>:</span>
            <input 
              type="number" 
              value={deadlineMinute} 
              onChange={(e) => setDeadlineMinute(Math.min(59, Math.max(0, parseInt(e.target.value) || 0)))}
              min={0} 
              max={59} 
              style={{ width: '45px', padding: '4px 6px', border: '1px solid var(--border)', borderRadius: '6px', background: 'var(--surface)', color: 'var(--text-primary)', textAlign: 'center', fontSize: '0.85rem' }} 
            />
          </div>
          
          <button onClick={fetchReportData} className="btn" style={{ gap: '0.35rem' }} disabled={isLoading}>
            <RefreshCw size={16} />
            Làm mới
          </button>
          <button onClick={handleExportCSV} className="btn btn-primary" style={{ gap: '0.35rem' }} disabled={isLoading || rows.length === 0}>
            <Download size={16} />
            Xuất báo cáo CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="zuzo-card" style={{ backgroundColor: 'var(--danger-bg)', border: '1px solid rgba(197, 34, 31, 0.2)', color: 'var(--danger)', padding: '1rem', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Grid Báo cáo */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        {/* Thống kê đếm tổng hợp */}
        <div className="zuzo-card" style={{ marginBottom: 0 }}>
          <div className="grid-3" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: 0 }}>
            
            <div style={{ borderRight: '1px solid var(--border)', paddingRight: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                <Users size={14} /> Có mặt
              </div>
              <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--success)', marginTop: '0.25rem' }}>{summary.present}</div>
            </div>

            <div style={{ borderRight: '1px solid var(--border)', paddingRight: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                <BookOpen size={14} /> Đi muộn
              </div>
              <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--warning)', marginTop: '0.25rem' }}>{summary.late}</div>
            </div>

            <div style={{ borderRight: '1px solid var(--border)', paddingRight: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                <Award size={14} /> Vắng mặt
              </div>
              <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--danger)', marginTop: '0.25rem' }}>{summary.absent}</div>
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                <Calendar size={14} /> Tổng số
              </div>
              <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.25rem' }}>{summary.total}</div>
            </div>
            
          </div>
        </div>

        {/* Bảng báo cáo chi tiết */}
        <div className="zuzo-card" style={{ marginBottom: 0 }}>
          <h3 className="zuzo-card-title">Kết Quả Điểm Danh Chi Tiết</h3>
          
          <div className="table-container">
            <table className="zuzo-table">
              <thead>
                <tr>
                  <th>MSSV</th>
                  <th>Họ và Tên</th>
                  <th>Giờ điểm danh</th>
                  <th style={{ textAlign: 'right' }}>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr key={idx}>
                    <td className="mono">{row.mssv}</td>
                    <td style={{ fontWeight: 600 }}>{row.full_name}</td>
                    <td className="mono">{row.time}</td>
                    <td style={{ textAlign: 'right' }}>
                      <span className={`badge badge-${row.status.toLowerCase()}`}>
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      Không tìm thấy dữ liệu điểm danh nào trong hôm nay cho lớp này.
                    </td>
                  </tr>
                )}
                {isLoading && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>Đang tải báo cáo...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        
      </div>
    </div>
  );
};
