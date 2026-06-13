import React, { useEffect, useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { Play, Square, Camera, AlertTriangle, ShieldCheck } from 'lucide-react';

interface AttendanceRow {
  mssv: string;
  full_name: string;
  time: string;
  status: string;
}

interface TelemetryData {
  student_db_key: string;
  decision: string;
  confidence: number;
  distance: number;
  gap: number;
  created_at: string;
  liveness_score: number;
  liveness_label: string;
  attack_type: string | null;
  live_score: number;
  print_score: number;
  replay_score: number;
  spoof_score: number;
}

const formatTime = (timeStr: string | null | undefined) => {
  if (!timeStr) return '--:--:--';
  try {
    if (timeStr.includes('T')) {
      return timeStr.split('T')[1].split('.')[0];
    }
    const parts = timeStr.split(' ');
    if (parts.length > 1) {
      return parts[1].split('.')[0];
    }
    return timeStr;
  } catch (e) {
    return timeStr;
  }
};

export const LiveAttendance: React.FC = () => {
  const { selectedClassId, fetchWithAuth } = useApp();
  
  const [cameraIndex, setCameraIndex] = useState(0);
  const [deadlineHour, setDeadlineHour] = useState(8);
  const [deadlineMinute, setDeadlineMinute] = useState(0);
  
  const [isRunning, setIsRunning] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  
  const [attendanceRows, setAttendanceRows] = useState<AttendanceRow[]>([]);
  const [summary, setSummary] = useState({ present: 0, late: 0, absent: 0, unknown: 0, total: 0 });
  const [latestEvent, setLatestEvent] = useState<TelemetryData | null>(null);
  
  const [isLoading, setIsLoading] = useState(false);
  
  const statusPollingRef = useRef<any | null>(null);
  const dataPollingRef = useRef<any | null>(null);

  const syncCameraStatus = async () => {
    try {
      const data = await fetchWithAuth('/api/camera/status');
      setIsRunning(data.running);
      if (data.error) {
        setCameraError(data.error);
      } else {
        setCameraError(null);
      }
    } catch (err) {
      console.error('Lỗi sync camera status:', err);
    }
  };

  const fetchAttendanceData = async () => {
    if (!selectedClassId) return;
    try {
      const data = await fetchWithAuth(`/api/classes/${selectedClassId}/attendance/today?deadline_hour=${deadlineHour}&deadline_minute=${deadlineMinute}`);
      setAttendanceRows(data.rows);
      setSummary(data.summary);
    } catch (err) {
      console.error('Lỗi lấy dữ liệu điểm danh:', err);
    }
  };

  const fetchLatestTelemetryEvent = async () => {
    if (!selectedClassId || !isRunning) return;
    try {
      const data = await fetchWithAuth(`/api/recognition/events?class_id=${selectedClassId}&limit=1`);
      if (data.rows && data.rows.length > 0) {
        setLatestEvent(data.rows[0]);
      }
    } catch (err) {
      console.error('Lỗi lấy telemetry event:', err);
    }
  };

  // Khởi chạy khi load page hoặc đổi lớp học
  useEffect(() => {
    syncCameraStatus();
    fetchAttendanceData();
    
    // Polling status camera định kỳ 2 giây
    statusPollingRef.current = setInterval(syncCameraStatus, 2000);
    
    return () => {
      if (statusPollingRef.current) clearInterval(statusPollingRef.current);
      if (dataPollingRef.current) clearInterval(dataPollingRef.current);
    };
  }, [selectedClassId]);

  // Polling data điểm danh và telemetry khi camera đang chạy
  useEffect(() => {
    if (isRunning) {
      dataPollingRef.current = setInterval(() => {
        fetchAttendanceData();
        fetchLatestTelemetryEvent();
      }, 2000);
    } else {
      if (dataPollingRef.current) {
        clearInterval(dataPollingRef.current);
      }
    }
    
    return () => {
      if (dataPollingRef.current) clearInterval(dataPollingRef.current);
    };
  }, [isRunning]);

  const handleStartCamera = async () => {
    if (!selectedClassId) return;
    setIsLoading(true);
    setCameraError(null);
    setLatestEvent(null);

    try {
      await fetchWithAuth(`/api/classes/${selectedClassId}/camera/start`, {
        method: 'POST',
        body: JSON.stringify({
          camera_index: cameraIndex,
          deadline_hour: deadlineHour,
          deadline_minute: deadlineMinute,
          profile: 'default'
        })
      });
      setIsRunning(true);
      await fetchAttendanceData();
    } catch (err: any) {
      setCameraError(err.message || 'Khởi động camera native thất bại.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopCamera = async () => {
    setIsLoading(true);
    try {
      await fetchWithAuth('/api/camera/stop', { method: 'POST' });
      setIsRunning(false);
      await fetchAttendanceData();
    } catch (err: any) {
      setCameraError(err.message || 'Lỗi dừng camera native.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearAttendance = async () => {
    if (!selectedClassId) return;
    if (!window.confirm('Bạn có chắc muốn xóa lịch sử điểm danh của lớp trong hôm nay? Dữ liệu này không thể phục hồi.')) return;
    
    try {
      await fetchWithAuth(`/api/classes/${selectedClassId}/attendance/clear-today`, { method: 'POST' });
      setLatestEvent(null);
      await fetchAttendanceData();
    } catch (err: any) {
      alert(err.message || 'Xóa lịch sử điểm danh thất bại.');
    }
  };

  const handleExportCSV = async () => {
    if (!selectedClassId) return;
    try {
      const res = await fetchWithAuth(`/api/classes/${selectedClassId}/attendance/export.csv`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `attendance_class_${selectedClassId}_export.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert('Lỗi xuất tệp tin báo cáo CSV.');
    }
  };

  if (!selectedClassId) {
    return (
      <div className="zuzo-card" style={{ minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
        <div>
          <span style={{ fontSize: '3rem', opacity: 0.1, display: 'block', marginBottom: '1rem' }}>🎓</span>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 500, marginBottom: '0.5rem' }}>Chưa chọn lớp học</h2>
          <p style={{ color: 'var(--text-muted)' }}>Vui lòng chọn lớp học ở thanh điều hướng phía trên để mở bảng điểm danh Live.</p>
        </div>
      </div>
    );
  }

  // Liveness Warning conditions
  const isPADModelMissing = latestEvent?.liveness_label === 'UNKNOWN' && latestEvent?.liveness_score === 0;

  return (
    <div style={{ padding: '1rem', backgroundColor: 'var(--console-bg)', borderRadius: '16px', border: '1px solid #2b2925' }} className="console-dark">
      {/* Header Console */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #2b2925', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ✣ Live Attendance Console
          </span>
          <h1 className="font-display" style={{ fontSize: '2.2rem', fontWeight: 500, color: '#ffffff', marginTop: '0.25rem' }}>
            Giám Sát Thời Gian Thực
          </h1>
        </div>
        <span
          className="badge"
          style={{
            height: '26px',
            fontSize: '0.75rem',
            backgroundColor: isRunning ? 'rgba(34, 197, 94, 0.15)' : 'rgba(107, 114, 128, 0.15)',
            color: isRunning ? '#22c55e' : '#9ca3af',
            border: `1px solid ${isRunning ? '#22c55e' : '#6b7280'}`
          }}
        >
          {isRunning ? 'LIVE' : 'SẴN SÀNG'}
        </span>
      </div>

      {cameraError && (
        <div className="zuzo-card" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', padding: '1rem', marginBottom: '1.5rem' }}>
          <AlertTriangle size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
          {cameraError}
        </div>
      )}

      {/* Grid Layout 3 cột */}
      <div className="grid-3" style={{ gridTemplateColumns: '320px 1fr 400px', gap: '1.5rem' }}>
        
        {/* Cột 1: Điều khiển camera */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="zuzo-card console-dark" style={{ border: '1px solid #2b2925', marginBottom: 0 }}>
            <h4 className="form-label" style={{ marginBottom: '1rem', color: '#ffffff' }}>Cấu hình Camera</h4>
            
            <div className="form-group">
              <label className="form-label">Cổng Camera (Index)</label>
              <input
                type="number"
                className="form-input"
                value={cameraIndex}
                onChange={(e) => setCameraIndex(Number(e.target.value))}
                min={0}
                max={5}
                disabled={isRunning || isLoading}
              />
            </div>

            <div className="form-group" style={{ display: 'flex', gap: '0.5rem' }}>
              <div style={{ flex: 1 }}>
                <label className="form-label">Giờ muộn</label>
                <input
                  type="number"
                  className="form-input"
                  value={deadlineHour}
                  onChange={(e) => setDeadlineHour(Number(e.target.value))}
                  min={0}
                  max={23}
                  disabled={isRunning || isLoading}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label className="form-label">Phút muộn</label>
                <input
                  type="number"
                  className="form-input"
                  value={deadlineMinute}
                  onChange={(e) => setDeadlineMinute(Number(e.target.value))}
                  min={0}
                  max={59}
                  disabled={isRunning || isLoading}
                />
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {isRunning ? (
                <button onClick={handleStopCamera} className="btn btn-primary" style={{ backgroundColor: '#ef4444', borderColor: '#ef4444', color: '#ffffff', width: '100%', gap: '0.5rem' }} disabled={isLoading}>
                  <Square size={16} fill="#ffffff" />
                  Dừng camera native
                </button>
              ) : (
                <button onClick={handleStartCamera} className="btn btn-primary" style={{ width: '100%', gap: '0.5rem' }} disabled={isLoading}>
                  <Play size={16} fill="#ffffff" />
                  Khởi động camera native
                </button>
              )}
            </div>
          </div>
          
          {/* Hướng dẫn Camera Native */}
          <div className="zuzo-card console-dark" style={{ border: '1px solid #2b2925', fontSize: '0.8rem', color: '#a09d96', marginBottom: 0 }}>
            <Camera size={20} style={{ color: 'var(--primary)', marginBottom: '0.5rem' }} />
            <p style={{ fontWeight: 600, color: '#ffffff', marginBottom: '0.25rem' }}>Giao diện Native:</p>
            <p>
              Camera sẽ được mở trong một cửa sổ riêng trên máy chủ. Giao diện Web sẽ tự động đồng bộ trạng thái và hiển thị danh sách điểm danh thời gian thực bên phải.
            </p>
          </div>
        </div>

        {/* Cột 2: Viễn thông nhận diện và liveness */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Telemetry Panel */}
          <div className="zuzo-card console-dark" style={{ border: '1px solid #2b2925', flex: 1, marginBottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <h4 className="form-label" style={{ color: '#ffffff', marginBottom: '1.5rem' }}>Dữ liệu quét mới nhất</h4>
            
            {/* Liveness warning toàn cục */}
            {isPADModelMissing && (
              <div style={{ backgroundColor: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#f87171', borderRadius: '8px', padding: '0.75rem', marginBottom: '1.5rem', display: 'flex', gap: '0.5rem', fontSize: '0.8rem' }}>
                <AlertTriangle size={18} style={{ flexShrink: 0 }} />
                <div>
                  <strong>Lọc giả mạo gặp sự cố (PAD error)</strong>
                  <p style={{ color: '#a09d96', marginTop: '0.25rem' }}>
                    Không thể phân tích Liveness. Giao diện điểm danh bị khóa (Fail-Closed) để bảo đảm bảo mật.
                  </p>
                </div>
              </div>
            )}

            {latestEvent ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h2 style={{ color: '#ffffff', fontSize: '2rem', fontFamily: 'var(--font-sans)', fontWeight: 700 }}>
                      {(latestEvent.student_db_key || 'UNKNOWN').replace(/_/g, ' ')}
                    </h2>
                    <span className="mono" style={{ fontSize: '0.85rem', color: '#a09d96' }}>
                      Sự kiện: {formatTime(latestEvent.created_at)}
                    </span>
                  </div>
                  <span
                    className="badge"
                    style={{
                      height: '24px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      backgroundColor: latestEvent.decision === 'ACCEPT' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                      color: latestEvent.decision === 'ACCEPT' ? '#22c55e' : '#f87171',
                      border: `1px solid ${latestEvent.decision === 'ACCEPT' ? '#22c55e' : '#ef4444'}`
                    }}
                  >
                    {latestEvent.decision || 'UNKNOWN'}
                  </span>
                </div>

                <div className="telemetry-grid">
                  <span className="telemetry-label">Nhận diện:</span>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#ffffff' }}>
                      <span className="mono">Confidence</span>
                      <span className="mono">
                        {latestEvent.confidence !== null && latestEvent.confidence !== undefined
                          ? `${(latestEvent.confidence * 100).toFixed(0)}%`
                          : '--'}
                      </span>
                    </div>
                    <div className="score-bar-container">
                      <div
                        className="score-bar"
                        style={{
                          width: `${
                            latestEvent.confidence !== null && latestEvent.confidence !== undefined
                              ? latestEvent.confidence * 100
                              : 0
                          }%`
                        }}
                      />
                    </div>
                  </div>

                  <span className="telemetry-label">Liveness:</span>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <span
                        className="badge"
                        style={{
                          height: '20px',
                          fontSize: '0.7rem',
                          backgroundColor:
                            (latestEvent.liveness_label || 'UNKNOWN') === 'LIVE'
                              ? 'rgba(34,197,94,0.15)'
                              : 'rgba(239,68,68,0.15)',
                          color: (latestEvent.liveness_label || 'UNKNOWN') === 'LIVE' ? '#22c55e' : '#f87171'
                        }}
                      >
                        {(latestEvent.liveness_label || 'UNKNOWN') === 'LIVE'
                          ? 'LIVE CLEAR'
                          : `${latestEvent.liveness_label || 'UNKNOWN'} REJECTED`}
                      </span>
                      <span className="mono" style={{ fontSize: '0.8rem', color: '#ffffff' }}>
                        {latestEvent.liveness_score !== null && latestEvent.liveness_score !== undefined
                          ? `${(latestEvent.liveness_score * 100).toFixed(0)}%`
                          : '--'}
                      </span>
                    </div>
                    <div className="score-bar-container">
                      <div
                        className={`score-bar ${
                          (latestEvent.liveness_label || 'UNKNOWN') === 'LIVE' ? 'liveness' : 'spoof'
                        }`}
                        style={{
                          width: `${
                            latestEvent.liveness_score !== null && latestEvent.liveness_score !== undefined
                              ? latestEvent.liveness_score * 100
                              : 0
                          }%`
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* PAD Scores Grid */}
                <div style={{ borderTop: '1px solid #2b2925', paddingTop: '1.25rem' }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#a09d96', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
                    Chi tiết điểm số PAD (MiniFASNet)
                  </div>
                  <div className="grid-2" style={{ gap: '0.75rem' }}>
                    <div style={{ backgroundColor: '#252320', padding: '0.5rem 0.75rem', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                      <span style={{ color: '#a09d96' }}>Live Score</span>
                      <span className="mono" style={{ color: '#ffffff', fontWeight: 600 }}>
                        {latestEvent.live_score !== null && latestEvent.live_score !== undefined
                          ? latestEvent.live_score.toFixed(3)
                          : '--'}
                      </span>
                    </div>
                    <div style={{ backgroundColor: '#252320', padding: '0.5rem 0.75rem', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                      <span style={{ color: '#a09d96' }}>Spoof Score</span>
                      <span
                        className="mono"
                        style={{
                          color:
                            latestEvent.spoof_score !== null &&
                            latestEvent.spoof_score !== undefined &&
                            latestEvent.spoof_score > 0.3
                              ? '#ef4444'
                              : '#ffffff',
                          fontWeight: 600
                        }}
                      >
                        {latestEvent.spoof_score !== null && latestEvent.spoof_score !== undefined
                          ? latestEvent.spoof_score.toFixed(3)
                          : '--'}
                      </span>
                    </div>
                    <div style={{ backgroundColor: '#252320', padding: '0.5rem 0.75rem', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                      <span style={{ color: '#a09d96' }}>Print Attack</span>
                      <span className="mono" style={{ color: '#ffffff' }}>
                        {latestEvent.print_score !== null && latestEvent.print_score !== undefined
                          ? latestEvent.print_score.toFixed(3)
                          : '--'}
                      </span>
                    </div>
                    <div style={{ backgroundColor: '#252320', padding: '0.5rem 0.75rem', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                      <span style={{ color: '#a09d96' }}>Replay Attack</span>
                      <span className="mono" style={{ color: '#ffffff' }}>
                        {latestEvent.replay_score !== null && latestEvent.replay_score !== undefined
                          ? latestEvent.replay_score.toFixed(3)
                          : '--'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#a09d96' }}>
                <ShieldCheck size={36} style={{ color: '#5c5952', marginBottom: '0.5rem', display: 'block', margin: '0 auto 0.5rem' }} />
                <span>Chờ dữ liệu nhận diện...</span>
              </div>
            )}
          </div>
        </div>

        {/* Cột 3: Bảng điểm danh thời gian thực */}
        <div className="zuzo-card console-dark" style={{ border: '1px solid #2b2925', marginBottom: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', borderBottom: '1px solid #2b2925', paddingBottom: '0.5rem' }}>
            <h4 style={{ color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: '0.9rem', fontWeight: 600 }}>Điểm Danh Lớp học</h4>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={handleExportCSV} className="btn" style={{ height: '28px', fontSize: '0.75rem', padding: '0 0.5rem' }}>
                Xuất CSV
              </button>
              <button onClick={handleClearAttendance} className="btn btn-danger" style={{ height: '28px', fontSize: '0.75rem', padding: '0 0.5rem' }}>
                Reset
              </button>
            </div>
          </div>

          {/* Counts */}
          <div style={{ display: 'flex', justifyContent: 'space-between', backgroundColor: '#252320', borderRadius: '8px', padding: '0.75rem', marginBottom: '1rem', fontSize: '0.8rem' }}>
            <div>Có mặt: <span className="mono" style={{ color: '#22c55e', fontWeight: 700 }}>{summary.present}</span></div>
            <div>Muộn: <span className="mono" style={{ color: '#eab308', fontWeight: 700 }}>{summary.late}</span></div>
            <div>Vắng: <span className="mono" style={{ color: '#ef4444', fontWeight: 700 }}>{summary.absent}</span></div>
            <div>Tổng: <span className="mono" style={{ color: '#ffffff', fontWeight: 700 }}>{summary.total}</span></div>
          </div>

          {/* Table */}
          <div className="table-container" style={{ flex: 1, maxHeight: '420px' }}>
            <table className="zuzo-table">
              <thead>
                <tr>
                  <th>MSSV</th>
                  <th>Sinh viên</th>
                  <th style={{ textAlign: 'right' }}>Thời gian</th>
                </tr>
              </thead>
              <tbody>
                {attendanceRows.filter(row => row.status === 'PRESENT' || row.status === 'LATE').map((row, idx) => (
                  <tr key={idx}>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>{row.mssv}</td>
                    <td style={{ fontWeight: 600, fontSize: '0.85rem' }}>{row.full_name}</td>
                    <td style={{ textAlign: 'right' }}>
                      <span className={`badge badge-${row.status.toLowerCase()}`} style={{ fontSize: '0.7rem', height: '18px' }}>
                        {row.time}
                      </span>
                    </td>
                  </tr>
                ))}
                {attendanceRows.filter(row => row.status === 'PRESENT' || row.status === 'LATE').length === 0 && (
                  <tr>
                    <td colSpan={3} style={{ textAlign: 'center', padding: '2rem', color: '#a09d96', fontSize: '0.85rem' }}>
                      Chưa ghi nhận điểm danh.
                    </td>
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
