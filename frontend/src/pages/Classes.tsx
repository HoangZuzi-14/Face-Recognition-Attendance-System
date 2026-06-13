import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Plus, Trash2, Download, Upload, Check, X, Users, UserX } from 'lucide-react';

interface Student {
  mssv: string;
  full_name: string;
  db_key: string | null;
}

export const Classes: React.FC = () => {
  const { selectedClassId, setSelectedClassId, classes, fetchClasses, fetchWithAuth, user } = useApp();
  const navigate = useNavigate();
  const [students, setStudents] = useState<Student[]>([]);
  const [newClassName, setNewClassName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteConfirmName, setDeleteConfirmName] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchRoster = async () => {
    if (!selectedClassId) {
      setStudents([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchWithAuth(`/api/classes/${selectedClassId}/roster`);
      setStudents(data.students);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Lỗi không thể tải danh sách sinh viên.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRoster();
    setSuccess(null);
  }, [selectedClassId]);

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassName.trim()) return;
    setError(null);
    setSuccess(null);

    try {
      const data = await fetchWithAuth('/api/classes', {
        method: 'POST',
        body: JSON.stringify({ class_name: newClassName })
      });
      setSuccess(`Tạo lớp học "${newClassName}" thành công.`);
      setNewClassName('');
      await fetchClasses();
      setSelectedClassId(data.id);
    } catch (err: any) {
      setError(err.message || 'Tạo lớp học thất bại.');
    }
  };

  const handleDeleteClass = async () => {
    if (!selectedClassId) return;
    const targetClass = classes.find(c => c.id === selectedClassId);
    if (!targetClass) return;

    if (deleteConfirmName !== targetClass.class_name) {
      setError('Tên lớp học xác nhận không trùng khớp.');
      return;
    }

    setIsDeleting(true);
    setError(null);
    setSuccess(null);

    try {
      await fetchWithAuth(`/api/classes/${selectedClassId}`, {
        method: 'DELETE'
      });
      setSuccess(`Đã xóa lớp học "${targetClass.class_name}".`);
      setShowDeleteModal(false);
      setDeleteConfirmName('');
      setSelectedClassId(null);
      await fetchClasses();
    } catch (err: any) {
      setError(err.message || 'Xóa lớp học thất bại.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const res = await fetchWithAuth('/api/roster/template.csv');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'roster_template.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      setError('Không thể tải file template mẫu.');
    }
  };

  const handleApplyDefaultRoster = async () => {
    if (!selectedClassId) return;
    setError(null);
    setSuccess(null);
    setIsLoading(true);
    try {
      const data = await fetchWithAuth(`/api/classes/${selectedClassId}/roster/default`, {
        method: 'POST'
      });
      setSuccess(`Áp dụng danh sách mặc định thành công: Thêm ${data.added} sinh viên.`);
      await fetchRoster();
    } catch (err: any) {
      setError(err.message || 'Lỗi áp dụng danh sách mặc định.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleImportRoster = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClassId || !file) return;
    setIsUploading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData();
    formData.append('file', file);

    const activeToken = localStorage.getItem('token');

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/classes/${selectedClassId}/roster/import`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${activeToken}`
        },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Lỗi upload danh sách.');
      }

      const data = await res.json();
      setSuccess(`Nhập danh sách thành công: Đã thêm ${data.added} sinh viên.`);
      setFile(null);
      await fetchRoster();
    } catch (err: any) {
      setError(err.message || 'Lỗi tải lên danh sách.');
    } finally {
      setIsUploading(false);
    }
  };

  const isTeacherOrAdmin = user?.role === 'admin' || user?.role === 'teacher';
  const isAdmin = user?.role === 'admin';

  return (
    <div>
      {/* Header trang */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 className="font-display" style={{ fontSize: '2.5rem', fontWeight: 500 }}>Lớp học & Danh sách</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Quản lý các lớp học và quản trị danh sách Roster sinh viên của từng lớp.</p>
      </div>

      {success && (
        <div className="zuzo-card" style={{ backgroundColor: 'var(--success-bg)', border: '1px solid rgba(19, 115, 51, 0.2)', color: 'var(--success)', padding: '1rem', marginBottom: '1.5rem' }}>
          {success}
        </div>
      )}

      {error && (
        <div className="zuzo-card" style={{ backgroundColor: 'var(--danger-bg)', border: '1px solid rgba(197, 34, 31, 0.2)', color: 'var(--danger)', padding: '1rem', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Grid Layout chính */}
      <div className="grid-2" style={{ gridTemplateColumns: '320px 1fr' }}>
        {/* Cột trái: Quản lý Lớp học */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="zuzo-card" style={{ marginBottom: 0 }}>
            <h3 className="zuzo-card-title" style={{ fontSize: '1.25rem' }}>Lớp Học</h3>
            
            {/* Lớp selector dạng List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto', marginBottom: '1.5rem', paddingRight: '0.25rem' }}>
              {classes.map((cls) => (
                <button
                  key={cls.id}
                  onClick={() => setSelectedClassId(cls.id)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid',
                    borderColor: selectedClassId === cls.id ? 'var(--primary)' : 'var(--border)',
                    backgroundColor: selectedClassId === cls.id ? 'var(--surface-raised)' : 'transparent',
                    color: selectedClassId === cls.id ? 'var(--primary)' : 'var(--text-primary)',
                    borderRadius: '8px',
                    textAlign: 'left',
                    fontWeight: selectedClassId === cls.id ? 600 : 500,
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  {cls.class_name}
                </button>
              ))}
              {classes.length === 0 && (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '1rem' }}>Chưa có lớp học nào.</div>
              )}
            </div>

            {/* Form tạo lớp mới (chỉ Admin mới tạo được theo spec gating) */}
            {isAdmin && (
              <form onSubmit={handleCreateClass} style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
                <div className="form-group">
                  <label className="form-label">Tạo lớp học mới</label>
                  <input
                    type="text"
                    className="form-input"
                    value={newClassName}
                    onChange={(e) => setNewClassName(e.target.value)}
                    placeholder="Tên lớp..."
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%', gap: '0.35rem' }}>
                  <Plus size={16} /> Tạo lớp mới
                </button>
              </form>
            )}
            
            {/* Nút xóa lớp dành riêng cho Admin */}
            {isAdmin && selectedClassId && (
              <button
                onClick={() => setShowDeleteModal(true)}
                className="btn btn-danger"
                style={{ width: '100%', marginTop: '1rem', gap: '0.35rem' }}
              >
                <Trash2 size={16} /> Xóa lớp học này
              </button>
            )}
          </div>
        </div>

        {/* Cột phải: Quản lý Roster học sinh của lớp được chọn */}
        <div className="zuzo-card" style={{ marginBottom: 0 }}>
          {selectedClassId ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
                <h3 className="zuzo-card-title" style={{ marginBottom: 0 }}>
                  Danh Sách Lớp (Roster)
                </h3>
                
                {/* Roster Controls (chỉ Teacher/Admin) */}
                {isTeacherOrAdmin && (
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <button onClick={handleDownloadTemplate} className="btn" title="Tải file mẫu CSV" style={{ gap: '0.35rem' }}>
                      <Download size={16} /> Mẫu CSV
                    </button>
                    <button onClick={handleApplyDefaultRoster} className="btn" title="Áp dụng danh sách mặc định" style={{ gap: '0.35rem' }} disabled={isLoading}>
                      <Users size={16} /> Roster Mẫu
                    </button>
                  </div>
                )}
              </div>

              {/* Upload Panel */}
              {isTeacherOrAdmin && (
                <div className="zuzo-card" style={{ backgroundColor: 'var(--surface-raised)', padding: '1rem', marginBottom: '1.5rem' }}>
                  <form onSubmit={handleImportRoster} style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: '200px' }}>
                      <input
                        type="file"
                        accept=".csv,.xlsx,.xls"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        style={{ display: 'none' }}
                        id="roster-uploader"
                      />
                      <label
                        htmlFor="roster-uploader"
                        className="btn"
                        style={{ width: '100%', borderStyle: 'dashed', borderColor: 'var(--primary)', cursor: 'pointer', height: '40px', justifyContent: 'flex-start', gap: '0.5rem' }}
                      >
                        <Upload size={16} />
                        {file ? file.name : 'Chọn file danh sách (.csv, .xlsx)...'}
                      </label>
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={!file || isUploading}>
                      {isUploading ? 'Đang nhập...' : 'Tải lên & Lưu'}
                    </button>
                  </form>
                </div>
              )}

              {/* Roster Table */}
              <div className="table-container">
                <table className="zuzo-table">
                  <thead>
                    <tr>
                      <th>MSSV</th>
                      <th>Họ và Tên</th>
                      <th>Face Key</th>
                      <th style={{ textAlign: 'right' }}>Khuôn mặt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((student, idx) => (
                      <tr key={idx}>
                        <td className="mono">{student.mssv}</td>
                        <td style={{ fontWeight: 600 }}>{student.full_name}</td>
                        <td className="mono" style={{ color: student.db_key ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                          {student.db_key || 'Chưa liên kết'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {student.db_key ? (
                            <span className="badge badge-present" style={{ gap: '0.25rem' }}>
                              <Check size={12} /> Đã liên kết
                            </span>
                          ) : (
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                              <span className="badge badge-unknown" style={{ gap: '0.25rem' }}>
                                <X size={12} /> Chưa đăng ký
                              </span>
                              {isTeacherOrAdmin && (
                                <button
                                  onClick={() => navigate('/enrollment')}
                                  className="btn"
                                  style={{ height: '24px', padding: '0 0.5rem', fontSize: '0.75rem', borderColor: 'var(--primary)', color: 'var(--primary)' }}
                                >
                                  Enroll
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                    {students.length === 0 && !isLoading && (
                      <tr>
                        <td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                          Lớp chưa có sinh viên nào. Vui lòng import danh sách.
                        </td>
                      </tr>
                    )}
                    {isLoading && (
                      <tr>
                        <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>Đang tải danh sách sinh viên...</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div style={{ minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', color: 'var(--text-muted)' }}>
              <div>
                <UserX size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
                <p style={{ fontWeight: 500 }}>Vui lòng chọn hoặc tạo lớp ở bảng điều khiển bên trái để xem danh sách sinh viên.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="zuzo-card" style={{ width: '450px', backgroundColor: '#ffffff', border: 'none', boxShadow: '0 8px 30px rgba(0,0,0,0.15)' }}>
            <h3 className="zuzo-card-title" style={{ color: 'var(--danger)' }}>Cảnh báo xóa lớp</h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
              Hành động này sẽ xóa hoàn toàn lớp học, toàn bộ danh sách sinh viên liên kết và lịch sử điểm danh của lớp. Thao tác này KHÔNG THỂ HOÀN TÁC.
            </p>
            
            <div className="form-group">
              <label className="form-label" style={{ color: 'var(--danger)' }}>
                Nhập tên lớp học để xác nhận xóa:
              </label>
              <input
                type="text"
                className="form-input"
                value={deleteConfirmName}
                onChange={(e) => setDeleteConfirmName(e.target.value)}
                placeholder="Nhập tên lớp..."
                required
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button onClick={() => { setShowDeleteModal(false); setDeleteConfirmName(''); }} className="btn" disabled={isDeleting}>
                Hủy bỏ
              </button>
              <button
                onClick={handleDeleteClass}
                className="btn btn-primary"
                style={{ backgroundColor: 'var(--danger)', borderColor: 'var(--danger)' }}
                disabled={isDeleting || deleteConfirmName !== classes.find(c => c.id === selectedClassId)?.class_name}
              >
                {isDeleting ? 'Đang xóa...' : 'Xác nhận xóa hoàn toàn'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
