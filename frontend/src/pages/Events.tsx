import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Filter, Eye, X, ShieldAlert, FileClock } from 'lucide-react';

interface EventRow {
  id: number;
  student_db_key: string;
  decision: string;
  confidence: number;
  distance: number;
  gap: number;
  created_at: string;
  liveness_score: number;
  liveness_label: string;
  attack_type: string | null;
  attendance_logged: boolean;
  live_score: number;
  print_score: number;
  replay_score: number;
  spoof_score: number;
}

interface StatsRow {
  decision: string;
  count: number;
  avg_confidence: number;
}

export const Events: React.FC = () => {
  const { selectedClassId, fetchWithAuth } = useApp();
  const [events, setEvents] = useState<EventRow[]>([]);
  const [stats, setStats] = useState<StatsRow[]>([]);
  const [filterDecision, setFilterDecision] = useState<string>('ALL');
  
  const [selectedEvent, setSelectedEvent] = useState<EventRow | null>(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isStatsOnly, setIsStatsOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = async () => {
    setIsLoading(true);
    setError(null);
    setIsStatsOnly(false);
    try {
      // Đầu tiên thử lấy danh sách sự kiện chi tiết
      const classParam = selectedClassId ? `?class_id=${selectedClassId}` : '';
      const data = await fetchWithAuth(`/api/recognition/events${classParam}`);
      setEvents(data.rows);
      
      // Lấy song song thống kê tổng hợp
      const statsData = await fetchWithAuth(`/api/recognition/stats${classParam}`);
      setStats(statsData.rows);
    } catch (err: any) {
      console.warn('Lỗi lấy sự kiện chi tiết, chuyển sang Stats-only Mode:', err);
      // Fallback sang Stats-only Mode
      setIsStatsOnly(true);
      try {
        const classParam = selectedClassId ? `?class_id=${selectedClassId}` : '';
        const statsData = await fetchWithAuth(`/api/recognition/stats${classParam}`);
        setStats(statsData.rows);
      } catch (statsErr: any) {
        setError(statsErr.message || 'Không thể tải dữ liệu thống kê sự kiện.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    setSelectedEvent(null);
  }, [selectedClassId]);

  const filteredEvents = events.filter((e) => {
    if (filterDecision === 'ALL') return true;
    if (filterDecision === 'ACCEPT') return e.decision === 'ACCEPT';
    if (filterDecision === 'SPOOF') return e.liveness_label === 'SPOOF' || e.decision === 'REJECT_SPOOF';
    if (filterDecision === 'UNKNOWN') return e.decision === 'UNKNOWN' || e.decision === 'REJECT_UNKNOWN';
    return true;
  });

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

  return (
    <div>
      {/* Header trang */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 className="font-display" style={{ fontSize: '2.5rem', fontWeight: 500 }}>Nhật ký nhận diện (Events)</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Xem chi tiết lịch sử phân tích nhận diện khuôn mặt và chống giả mạo của camera.</p>
      </div>

      {error && (
        <div className="zuzo-card" style={{ backgroundColor: 'var(--danger-bg)', border: '1px solid rgba(197, 34, 31, 0.2)', color: 'var(--danger)', padding: '1rem', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Grid Layout phụ thuộc vào chế độ (Stats Only hay Full Table) */}
      <div className="grid-2" style={{ gridTemplateColumns: isStatsOnly ? '1fr' : '1fr 350px' }}>
        
        {/* Cột trái: Danh sách sự kiện hoặc Thống kê */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Panel bộ lọc (Chỉ hiển thị nếu không phải Stats Only) */}
          {!isStatsOnly && (
            <div className="zuzo-card" style={{ marginBottom: 0, padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  <Filter size={16} /> Lọc quyết định:
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {['ALL', 'ACCEPT', 'SPOOF', 'UNKNOWN'].map((dec) => (
                    <button
                      key={dec}
                      onClick={() => setFilterDecision(dec)}
                      className="btn"
                      style={{
                        height: '32px',
                        padding: '0 0.75rem',
                        fontSize: '0.75rem',
                        borderColor: filterDecision === dec ? 'var(--primary)' : 'var(--border)',
                        backgroundColor: filterDecision === dec ? 'var(--surface-raised)' : 'transparent',
                        color: filterDecision === dec ? 'var(--primary)' : 'var(--text-primary)'
                      }}
                    >
                      {dec === 'ALL' ? 'Tất cả' : dec}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Nội dung chính */}
          {isStatsOnly ? (
            // FALLBACK: Stats-only Mode
            <div className="zuzo-card" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', gap: '1rem', backgroundColor: 'var(--warning-bg)', color: 'var(--warning)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.85rem' }}>
                <FileClock size={20} style={{ flexShrink: 0 }} />
                <div>
                  <strong>Chế độ Thống Kê (Stats-only Mode)</strong>
                  <p style={{ color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    Backend hiện tại chưa bật cấu hình ghi nhận sự kiện nhận diện chi tiết hoặc API danh sách sự kiện trống. 
                    Dưới đây là bảng thống kê tổng hợp số liệu nhận diện.
                  </p>
                </div>
              </div>

              <h3 className="zuzo-card-title">Thống Kê Tổng Hợp</h3>
              <div className="table-container">
                <table className="zuzo-table">
                  <thead>
                    <tr>
                      <th>Quyết định (Decision)</th>
                      <th>Số lượt quét (Count)</th>
                      <th style={{ textAlign: 'right' }}>Độ tin cậy trung bình</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.map((row, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600 }}>{row.decision}</td>
                        <td className="mono">{row.count}</td>
                        <td className="mono" style={{ textAlign: 'right' }}>{(row.avg_confidence * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                    {stats.length === 0 && (
                      <tr>
                        <td colSpan={3} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Chưa có dữ liệu thống kê sự kiện.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            // TIÊU CHUẨN: Bảng danh sách sự kiện chi tiết
            <div className="zuzo-card" style={{ marginBottom: 0 }}>
              <div className="table-container">
                <table className="zuzo-table">
                  <thead>
                    <tr>
                      <th>Thời gian</th>
                      <th>Face Key</th>
                      <th>Quyết định</th>
                      <th>Liveness</th>
                      <th style={{ textAlign: 'right' }}>Chi tiết</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEvents.map((row, idx) => (
                      <tr key={idx}>
                        <td className="mono" style={{ fontSize: '0.8rem' }}>
                          {formatTime(row.created_at)}
                        </td>
                        <td style={{ fontWeight: 600 }}>{(row.student_db_key || 'UNKNOWN').replace(/_/g, ' ')}</td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              height: '20px',
                              fontSize: '0.7rem',
                              backgroundColor: row.decision === 'ACCEPT' ? 'var(--success-bg)' : 'var(--danger-bg)',
                              color: row.decision === 'ACCEPT' ? 'var(--success)' : 'var(--danger)'
                            }}
                          >
                            {row.decision}
                          </span>
                        </td>
                        <td>
                          <span className={`badge badge-${(row.liveness_label || 'UNKNOWN').toLowerCase()}`} style={{ fontSize: '0.7rem', height: '20px' }}>
                            {row.liveness_label || 'UNKNOWN'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedEvent(row)}
                            className="btn"
                            style={{ height: '26px', padding: '0 0.5rem', fontSize: '0.75rem', gap: '0.25rem' }}
                          >
                            <Eye size={12} /> Xem
                          </button>
                        </td>
                      </tr>
                    ))}
                    {filteredEvents.length === 0 && !isLoading && (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                          Không tìm thấy nhật ký sự kiện nào phù hợp.
                        </td>
                      </tr>
                    )}
                    {isLoading && (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>Đang tải danh sách sự kiện...</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Cột phải: Ngăn kéo (Drawer/Card) chi tiết sự kiện được chọn */}
        {!isStatsOnly && (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {selectedEvent ? (
              <div className="zuzo-card" style={{ marginBottom: 0, position: 'sticky', top: '80px', borderLeft: '3px solid var(--primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
                  <h4 style={{ fontWeight: 600, fontSize: '0.95rem' }}>Chi tiết Nhận diện</h4>
                  <button onClick={() => setSelectedEvent(null)} className="btn" style={{ width: '26px', height: '26px', padding: 0, border: 'none' }}>
                    <X size={16} />
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.85rem' }}>
                  <div>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Face DB Key:</span>
                    <div style={{ fontWeight: 700, fontSize: '1.2rem', marginTop: '0.25rem' }}>
                      {selectedEvent.student_db_key || 'UNKNOWN'}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Điểm nhận diện (Confidence):</span>
                    <div className="mono" style={{ fontWeight: 600, marginTop: '0.25rem' }}>
                      {(selectedEvent.confidence * 100).toFixed(1)}% (Distance: {selectedEvent.distance !== null && selectedEvent.distance !== undefined ? selectedEvent.distance.toFixed(3) : '--'})
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Trạng thái Liveness:</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                      <span className={`badge badge-${(selectedEvent.liveness_label || 'UNKNOWN').toLowerCase()}`}>
                        {selectedEvent.liveness_label || 'UNKNOWN'}
                      </span>
                      <span className="mono">{selectedEvent.liveness_score !== null && selectedEvent.liveness_score !== undefined ? (selectedEvent.liveness_score * 100).toFixed(1) : '--'}%</span>
                    </div>
                  </div>

                  {/* Liveness Scores Mini Grid */}
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: '0.5rem' }}>Phân tích chống giả mạo:</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Ảnh in (Print Score)</span>
                        <span className="mono">{selectedEvent.print_score !== null && selectedEvent.print_score !== undefined ? selectedEvent.print_score.toFixed(3) : '--'}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Màn hình (Replay Score)</span>
                        <span className="mono">{selectedEvent.replay_score !== null && selectedEvent.replay_score !== undefined ? selectedEvent.replay_score.toFixed(3) : '--'}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Tổng Spoof Score</span>
                        <span className="mono" style={{ color: (selectedEvent.spoof_score || 0) > 0.3 ? 'var(--danger)' : 'inherit', fontWeight: 600 }}>
                          {selectedEvent.spoof_score !== null && selectedEvent.spoof_score !== undefined ? selectedEvent.spoof_score.toFixed(3) : '--'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Security Action logging */}
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Log điểm danh thành công:</span>
                    {selectedEvent.attendance_logged ? (
                      <span className="badge badge-present" style={{ height: '18px' }}>ĐÃ LƯU</span>
                    ) : (
                      <span className="badge badge-absent" style={{ height: '18px' }}>BỊ CHẶN</span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="zuzo-card" style={{ marginBottom: 0, padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', borderStyle: 'dashed' }}>
                <ShieldAlert size={24} style={{ opacity: 0.2, marginBottom: '0.5rem', display: 'block', margin: '0 auto 0.5rem' }} />
                <span style={{ fontSize: '0.85rem' }}>Chọn một sự kiện trong danh sách bên trái để xem phân tích chống giả mạo chi tiết.</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
