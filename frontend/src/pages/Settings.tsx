import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { ShieldAlert, CheckCircle, Database, Server, Clipboard } from 'lucide-react';

interface PreflightData {
  active_identity_count: number;
  face_db_status: string;
  face_db_path: string;
  sqlite_status: string;
  sqlite_db_path: string;
  liveness_enabled: boolean;
}

interface IntegrityReport {
  ok: boolean;
  students_missing_face_embeddings: string[];
  face_embeddings_missing_students: string[];
  missing_raw_dirs: string[];
  missing_processed_dirs: string[];
  attendance_keys_missing_students: string[];
  errors: string[];
}

interface AuditLogRow {
  timestamp?: string;
  action: string;
  target?: string;
  actor_username?: string;
  status: string;
  details?: string;
}

export const Settings: React.FC = () => {
  const { selectedClassId, fetchWithAuth } = useApp();
  const [activeTab, setActiveTab] = useState<'system' | 'integrity' | 'audit'>('system');
  const [preflight, setPreflight] = useState<PreflightData | null>(null);
  const [integrity, setIntegrity] = useState<IntegrityReport | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogRow[]>([]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSystemData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (selectedClassId) {
        const preflightData = await fetchWithAuth(`/api/classes/${selectedClassId}/camera/preflight`);
        setPreflight(preflightData);
      }
      const auditData = await fetchWithAuth('/api/audit/logs?limit=50');
      setAuditLogs(auditData.rows);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Lỗi không thể tải dữ liệu hệ thống.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemData();
  }, [selectedClassId, activeTab]);

  const handleRunIntegrityCheck = async () => {
    setIsLoading(true);
    setError(null);
    setIntegrity(null);
    try {
      const data = await fetchWithAuth('/api/integrity/check', { method: 'POST' });
      setIntegrity(data);
    } catch (err: any) {
      setError(err.message || 'Chạy kiểm tra toàn vẹn thất bại.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyIntegrityReport = () => {
    if (!integrity) return;
    const reportText = JSON.stringify(integrity, null, 2);
    navigator.clipboard.writeText(reportText);
    alert('Đã sao chép báo cáo toàn vẹn vào bộ nhớ tạm!');
  };

  return (
    <div>
      {/* Header trang */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 className="font-display" style={{ fontSize: '2.5rem', fontWeight: 500 }}>Hệ thống & Cài đặt</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Theo dõi cấu hình kỹ thuật, audit log và kiểm tra sự toàn vẹn của dữ liệu.</p>
      </div>

      {error && (
        <div className="zuzo-card" style={{ backgroundColor: 'var(--danger-bg)', border: '1px solid rgba(197, 34, 31, 0.2)', color: 'var(--danger)', padding: '1rem', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Tabs Menu */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
        <button
          onClick={() => setActiveTab('system')}
          className="btn"
          style={{
            height: '34px',
            borderColor: activeTab === 'system' ? 'var(--primary)' : 'var(--border)',
            backgroundColor: activeTab === 'system' ? 'var(--surface-raised)' : 'transparent',
            color: activeTab === 'system' ? 'var(--primary)' : 'var(--text-primary)'
          }}
        >
          Cấu hình hệ thống
        </button>
        <button
          onClick={() => setActiveTab('integrity')}
          className="btn"
          style={{
            height: '34px',
            borderColor: activeTab === 'integrity' ? 'var(--primary)' : 'var(--border)',
            backgroundColor: activeTab === 'integrity' ? 'var(--surface-raised)' : 'transparent',
            color: activeTab === 'integrity' ? 'var(--primary)' : 'var(--text-primary)'
          }}
        >
          Kiểm tra toàn vẹn (Integrity)
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className="btn"
          style={{
            height: '34px',
            borderColor: activeTab === 'audit' ? 'var(--primary)' : 'var(--border)',
            backgroundColor: activeTab === 'audit' ? 'var(--surface-raised)' : 'transparent',
            color: activeTab === 'audit' ? 'var(--primary)' : 'var(--text-primary)'
          }}
        >
          Nhật ký hệ thống (Audit Logs)
        </button>
      </div>

      {/* Tab 1: Cấu hình hệ thống */}
      {activeTab === 'system' && (
        <div className="zuzo-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <h3 className="zuzo-card-title">Tham Số Cấu Hình Kỹ Thuật</h3>
          
          <div className="grid-2">
            <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1.25rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <Server size={24} style={{ color: 'var(--primary)' }} />
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Cơ sở dữ liệu SQLite</div>
                <div className="mono" style={{ fontSize: '0.9rem', wordBreak: 'break-all', marginTop: '0.25rem' }}>
                  {preflight?.sqlite_db_path || 'app/attendance.db'}
                </div>
              </div>
            </div>

            <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1.25rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <Database size={24} style={{ color: 'var(--primary)' }} />
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Face Database Pickle File</div>
                <div className="mono" style={{ fontSize: '0.9rem', wordBreak: 'break-all', marginTop: '0.25rem' }}>
                  {preflight?.face_db_path || 'data/embeddings/db.pkl'}
                </div>
              </div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
            <h4 style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.95rem' }}>Trạng thái mô hình AI:</h4>
            <ul style={{ listStyleType: 'disc', paddingLeft: '1.5rem', fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <li>Mô hình trích xuất Embedding: <strong>InsightFace (Buffalo_L)</strong></li>
              <li>Mô hình Chống Giả Mạo: <strong>MiniFASNet (ONNX)</strong></li>
              <li>Trạng thái PAD Model: <span className="badge badge-present" style={{ height: '18px' }}>{preflight?.liveness_enabled ? 'ĐANG HOẠT ĐỘNG' : 'TẮT'}</span></li>
            </ul>
          </div>
        </div>
      )}

      {/* Tab 2: Kiểm tra toàn vẹn */}
      {activeTab === 'integrity' && (
        <div className="zuzo-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 className="zuzo-card-title" style={{ marginBottom: 0 }}>Đối Soát Đồng Bộ Dữ Liệu</h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {integrity && (
                <button onClick={handleCopyIntegrityReport} className="btn" style={{ gap: '0.35rem' }}>
                  <Clipboard size={16} /> Sao chép JSON
                </button>
              )}
              <button onClick={handleRunIntegrityCheck} className="btn btn-primary" style={{ gap: '0.35rem' }} disabled={isLoading}>
                {isLoading ? 'Đang kiểm tra...' : 'Bắt đầu kiểm tra toàn vẹn'}
              </button>
            </div>
          </div>

          {integrity ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {integrity.ok ? (
                <div style={{ backgroundColor: 'var(--success-bg)', border: '1px solid rgba(19, 115, 51, 0.2)', color: 'var(--success)', borderRadius: '8px', padding: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <CheckCircle size={20} />
                  <strong>Dữ liệu đồng bộ hoàn hảo! Không phát hiện điểm sai lệch nào giữa cơ sở dữ liệu SQLite, Face DB và thư mục ảnh.</strong>
                </div>
              ) : (
                <div style={{ backgroundColor: 'var(--danger-bg)', border: '1px solid rgba(197, 34, 31, 0.2)', color: 'var(--danger)', borderRadius: '8px', padding: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <ShieldAlert size={20} />
                  <strong>Phát hiện điểm sai lệch dữ liệu! Vui lòng đối soát các nhóm lỗi bên dưới.</strong>
                </div>
              )}

              {/* Danh sách lỗi chi tiết */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {integrity.students_missing_face_embeddings.length > 0 && (
                  <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--danger)', fontSize: '0.875rem' }}>Sinh viên có tên trong SQLite nhưng thiếu vector khuôn mặt (db.pkl):</div>
                    <ul className="mono" style={{ listStyleType: 'square', paddingLeft: '1.5rem', marginTop: '0.5rem', fontSize: '0.8rem' }}>
                      {integrity.students_missing_face_embeddings.map((s, idx) => <li key={idx}>{s}</li>)}
                    </ul>
                  </div>
                )}

                {integrity.face_embeddings_missing_students.length > 0 && (
                  <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--warning)', fontSize: '0.875rem' }}>Vector khuôn mặt trong db.pkl mồ côi (không gán cho sinh viên nào):</div>
                    <ul className="mono" style={{ listStyleType: 'square', paddingLeft: '1.5rem', marginTop: '0.5rem', fontSize: '0.8rem' }}>
                      {integrity.face_embeddings_missing_students.map((s, idx) => <li key={idx}>{s}</li>)}
                    </ul>
                  </div>
                )}

                {integrity.missing_raw_dirs.length > 0 && (
                  <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--warning)', fontSize: '0.875rem' }}>Thiếu thư mục ảnh raw trên ổ đĩa:</div>
                    <ul className="mono" style={{ listStyleType: 'square', paddingLeft: '1.5rem', marginTop: '0.5rem', fontSize: '0.8rem' }}>
                      {integrity.missing_raw_dirs.map((s, idx) => <li key={idx}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)', border: '1px dashed var(--border)', borderRadius: '8px' }}>
              Bấm nút "Bắt đầu kiểm tra toàn vẹn" phía trên để phân tích so khớp cơ sở dữ liệu.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Audit Logs */}
      {activeTab === 'audit' && (
        <div className="zuzo-card" style={{ marginBottom: 0 }}>
          <h3 className="zuzo-card-title">Lịch Sử Thao Tác Hệ Thống</h3>
          
          <div className="table-container" style={{ maxHeight: '450px' }}>
            <table className="zuzo-table">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Hành động</th>
                  <th>Đối tượng</th>
                  <th>Người thực hiện</th>
                  <th style={{ textAlign: 'right' }}>Kết quả</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((row, idx) => (
                  <tr key={idx}>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>
                      {row.timestamp ? row.timestamp.replace('T', ' ').split('.')[0] : '--'}
                    </td>
                    <td style={{ fontWeight: 600 }}>{row.action}</td>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>{row.target || '--'}</td>
                    <td>{row.actor_username || 'system'}</td>
                    <td style={{ textAlign: 'right' }}>
                      <span className={`badge badge-${row.status === 'SUCCESS' ? 'present' : 'absent'}`} style={{ height: '18px', fontSize: '0.7rem' }}>
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {auditLogs.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>Chưa có nhật ký hoạt động.</td>
                  </tr>
                )}
                {isLoading && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>Đang tải nhật ký...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
