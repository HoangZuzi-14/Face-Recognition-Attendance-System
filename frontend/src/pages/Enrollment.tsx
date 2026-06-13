import React, { useEffect, useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { Camera, RefreshCw, Info } from 'lucide-react';

interface Student {
  id: number;
  mssv: string;
  full_name: string;
  db_key: string | null;
}

export const Enrollment: React.FC = () => {
  const { selectedClassId, fetchWithAuth } = useApp();
  const [missingStudents, setMissingStudents] = useState<Student[]>([]);
  const [enrollMode, setEnrollMode] = useState<'roster' | 'free'>('roster');
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);

  const [personKey, setPersonKey] = useState('');
  const [fullName, setFullName] = useState('');
  const [mssv, setMssv] = useState('');

  const [cameraIndex, setCameraIndex] = useState(0);
  const [isCapturing, setIsCapturing] = useState(false);
  const [imageCount, setImageCount] = useState(0);
  const [isFinalizing, setIsFinalizing] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const pollingIntervalRef = useRef<any | null>(null);

  // Lấy danh sách sinh viên chưa có khuôn mặt
  const fetchMissingStudents = async () => {
    try {
      const data = await fetchWithAuth('/api/students?face=missing');
      // Nếu có selectedClassId, lọc sinh viên theo lớp học (thông qua bảng cs) bằng cách lấy roster lớp đó trước rồi lọc
      if (selectedClassId) {
        const rosterData = await fetchWithAuth(`/api/classes/${selectedClassId}/roster`);
        const rosterMssvs = rosterData.students.map((s: any) => s.mssv);
        const filtered = data.students.filter((s: Student) => rosterMssvs.includes(s.mssv));
        setMissingStudents(filtered);
      } else {
        setMissingStudents(data.students);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchMissingStudents();
    resetEnrollmentState();
  }, [selectedClassId, enrollMode]);

  const resetEnrollmentState = () => {
    setSelectedStudent(null);
    setPersonKey('');
    setFullName('');
    setMssv('');
    setImageCount(0);
    setIsCapturing(false);
    setError(null);
    setSuccess(null);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
  };

  const handleStudentSelect = (student: Student) => {
    setSelectedStudent(student);
    setMssv(student.mssv);
    setFullName(student.full_name);
    // Tự động gợi ý db_key: Full_Name_replace
    const suggestedKey = student.full_name
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Bỏ dấu tiếng Việt
      .replace(/[^\w\s]/gi, '')
      .replace(/\s+/g, '_');
    setPersonKey(`${suggestedKey}_${student.mssv}`);
  };

  // Bắt đầu chụp ảnh (gọi API camera capture native)
  const handleStartCapture = async () => {
    const key = enrollMode === 'roster' ? personKey : personKey.trim();
    if (!key) {
      setError('Vui lòng điền Face DB Key (Person Key) trước.');
      return;
    }

    setError(null);
    setSuccess(null);
    setIsCapturing(true);

    try {
      // Nếu đăng ký ở chế độ tự do, đảm bảo tạo học sinh và liên kết trong lớp trước
      if (enrollMode === 'free') {
        if (!fullName.trim()) {
          setError('Vui lòng nhập Họ và Tên sinh viên.');
          setIsCapturing(false);
          return;
        }
        await fetchWithAuth(`/api/classes/${selectedClassId || 1}/students`, {
          method: 'POST',
          body: JSON.stringify({
            full_name: fullName,
            db_key: key,
            mssv: mssv.trim() || undefined
          })
        });
      } else if (selectedStudent) {
        // Liên kết học sinh hiện có với db_key mới
        await fetchWithAuth(`/api/students/${selectedStudent.mssv}/face-link`, {
          method: 'POST',
          body: JSON.stringify({ db_key: key })
        });
      }

      // Khởi động native camera capture
      await fetchWithAuth('/api/faces/enroll/start', {
        method: 'POST',
        body: JSON.stringify({
          person_key: key,
          camera_index: cameraIndex,
          start_index: 0
        })
      });

      // Bắt đầu polling image count
      startPolling(key);
    } catch (err: any) {
      setError(err.message || 'Khởi động camera native thất bại.');
      setIsCapturing(false);
    }
  };

  const startPolling = (key: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const data = await fetchWithAuth(`/api/faces/enroll/status?person_key=${key}`);
        setImageCount(data.image_count);
        setIsCapturing(data.running);

        // Nếu tiến trình camera native tắt đi, ngắt interval
        if (!data.running) {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
        }
      } catch (err) {
        console.error('Lỗi polling trạng thái chụp:', err);
      }
    }, 1000);
  };

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Hoàn tất đăng ký khuôn mặt
  const handleFinalize = async () => {
    const key = personKey;
    setIsFinalizing(true);
    setError(null);
    setSuccess(null);

    try {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }

      const data = await fetchWithAuth('/api/faces/enroll/finalize', {
        method: 'POST',
        body: JSON.stringify({
          person_key: key,
          start_index: 0
        })
      });

      if (data.ok) {
        setSuccess(`Đăng ký thành công khuôn mặt cho sinh viên. Vector đặc trưng đã được cập nhật.`);
        resetEnrollmentState();
        fetchMissingStudents();
      } else {
        setError(data.message || 'Xử lý khuôn mặt thất bại.');
      }
    } catch (err: any) {
      setError(err.message || 'Lỗi lưu dữ liệu đăng ký.');
    } finally {
      setIsFinalizing(false);
    }
  };

  // Hủy đăng ký khuôn mặt
  const handleCancel = async () => {
    const key = personKey;
    setError(null);
    setSuccess(null);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    try {
      await fetchWithAuth('/api/faces/enroll/cancel', {
        method: 'POST',
        body: JSON.stringify({ person_key: key })
      });
      setSuccess('Đã hủy chụp và dọn dẹp các tệp tin lưu tạm.');
      resetEnrollmentState();
      fetchMissingStudents();
    } catch (err: any) {
      setError(err.message || 'Gặp lỗi khi gửi lệnh hủy bỏ.');
    }
  };

  return (
    <div>
      {/* Header trang */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 className="font-display" style={{ fontSize: '2.5rem', fontWeight: 500 }}>Đăng ký khuôn mặt (Enrollment)</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Thu thập hình ảnh chân dung sinh viên để xây dựng dữ liệu nhận diện.</p>
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
      <div className="grid-2" style={{ gridTemplateColumns: '400px 1fr' }}>
        {/* Cột trái: Chọn sinh viên / Nhập Person Key */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="zuzo-card" style={{ marginBottom: 0 }}>
            {/* Chuyển chế độ */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
              <button
                onClick={() => setEnrollMode('roster')}
                className="btn"
                style={{
                  flex: 1,
                  height: '34px',
                  borderColor: enrollMode === 'roster' ? 'var(--primary)' : 'var(--border)',
                  backgroundColor: enrollMode === 'roster' ? 'var(--surface-raised)' : 'transparent',
                  color: enrollMode === 'roster' ? 'var(--primary)' : 'var(--text-primary)'
                }}
                disabled={isCapturing}
              >
                Từ DS lớp
              </button>
              <button
                onClick={() => setEnrollMode('free')}
                className="btn"
                style={{
                  flex: 1,
                  height: '34px',
                  borderColor: enrollMode === 'free' ? 'var(--primary)' : 'var(--border)',
                  backgroundColor: enrollMode === 'free' ? 'var(--surface-raised)' : 'transparent',
                  color: enrollMode === 'free' ? 'var(--primary)' : 'var(--text-primary)'
                }}
                disabled={isCapturing}
              >
                Nhập tự do
              </button>
            </div>

            {enrollMode === 'roster' ? (
              <div>
                <label className="form-label" style={{ marginBottom: '0.5rem' }}>Chọn sinh viên chưa có ảnh</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
                  {missingStudents.map((student) => (
                    <button
                      key={student.id}
                      onClick={() => handleStudentSelect(student)}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: '1px solid',
                        borderColor: selectedStudent?.id === student.id ? 'var(--primary)' : 'var(--border)',
                        backgroundColor: selectedStudent?.id === student.id ? 'var(--surface-raised)' : 'transparent',
                        color: selectedStudent?.id === student.id ? 'var(--primary)' : 'var(--text-primary)',
                        borderRadius: '8px',
                        textAlign: 'left',
                        cursor: 'pointer',
                        fontSize: '0.875rem'
                      }}
                      disabled={isCapturing}
                    >
                      <div style={{ fontWeight: 600 }}>{student.full_name}</div>
                      <div className="mono" style={{ fontSize: '0.75rem', opacity: 0.7 }}>MSSV: {student.mssv}</div>
                    </button>
                  ))}
                  {missingStudents.length === 0 && (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '1rem' }}>
                      Không có sinh viên nào thiếu khuôn mặt.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              // Chế độ tự do
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Họ và Tên</label>
                  <input
                    type="text"
                    className="form-input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Ví dụ: Nguyen Van A"
                    required
                    disabled={isCapturing}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">MSSV (Mã số sinh viên)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={mssv}
                    onChange={(e) => setMssv(e.target.value)}
                    placeholder="Ví dụ: B20DCCN001"
                    disabled={isCapturing}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Face DB Key (Mã phân biệt)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={personKey}
                    onChange={(e) => setPersonKey(e.target.value)}
                    placeholder="Ví dụ: Nguyen_Van_A"
                    required
                    disabled={isCapturing}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Cột phải: Tiến trình chụp OpenCV */}
        <div className="zuzo-card" style={{ marginBottom: 0, display: 'flex', flexDirection: 'column' }}>
          <h3 className="zuzo-card-title">Hộp điều khiển Camera Native</h3>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '2rem', padding: '2rem 0' }}>
            {/* Camera Frame Mockup */}
            <div
              style={{
                width: '100%',
                height: '320px',
                backgroundColor: 'var(--console-bg)',
                borderRadius: '12px',
                border: '1px solid #2b2925',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#a09d96',
                textAlign: 'center',
                padding: '2rem',
                position: 'relative'
              }}
            >
              <Camera size={48} style={{ color: isCapturing ? 'var(--primary)' : '#5c5952', marginBottom: '1rem' }} />
              {isCapturing ? (
                <div>
                  <h4 style={{ color: '#ffffff', marginBottom: '0.5rem', fontFamily: 'var(--font-sans)' }}>Camera Native đang hoạt động...</h4>
                  <p style={{ fontSize: '0.85rem', maxWidth: '450px' }}>
                    Một cửa sổ OpenCV webcam đã được mở trên hệ thống.
                    Nhấn phím <strong style={{ color: '#ffffff' }}>SPACE</strong> trên cửa sổ camera đó để chụp ảnh hợp lệ.
                    Nhấn phím <strong style={{ color: '#ffffff' }}>Q hoặc ESC</strong> để tắt camera.
                  </p>
                </div>
              ) : (
                <div>
                  <h4 style={{ color: '#ffffff', marginBottom: '0.5rem', fontFamily: 'var(--font-sans)' }}>Thiết bị Camera sẵn sàng</h4>
                  <p style={{ fontSize: '0.85rem' }}>Bấm nút khởi động bên dưới để bắt đầu thu thập ảnh.</p>
                </div>
              )}

              {/* Progress indicator */}
              {isCapturing && (
                <div style={{ position: 'absolute', bottom: '1.5rem', left: '1.5rem', right: '1.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#ffffff', marginBottom: '0.25rem' }}>
                    <span>Ảnh đã lưu:</span>
                    <span className="mono">{imageCount} / 8</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', backgroundColor: '#2b2925', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(100, (imageCount / 8) * 100)}%`, height: '100%', backgroundColor: 'var(--primary)', transition: 'width 0.2s ease' }} />
                  </div>
                </div>
              )}
            </div>

            {/* Controls */}
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="form-label" style={{ marginBottom: 0 }}>Cổng Camera (Index):</span>
                <input
                  type="number"
                  className="form-input"
                  style={{ width: '80px', height: '38px' }}
                  value={cameraIndex}
                  onChange={(e) => setCameraIndex(Number(e.target.value))}
                  min={0}
                  max={5}
                  disabled={isCapturing}
                />
              </div>

              {!isCapturing && imageCount === 0 ? (
                <button
                  onClick={handleStartCapture}
                  className="btn btn-primary"
                  style={{ height: '40px', padding: '0 2rem' }}
                  disabled={!personKey}
                >
                  Bắt đầu chụp
                </button>
              ) : (
                <div style={{ display: 'flex', gap: '0.75rem', flex: 1 }}>
                  {isCapturing ? (
                    <button onClick={handleCancel} className="btn btn-danger" style={{ height: '40px' }}>
                      Hủy bỏ
                    </button>
                  ) : (
                    <>
                      <button onClick={handleStartCapture} className="btn" style={{ height: '40px' }}>
                        <RefreshCw size={16} /> Chụp thêm ảnh
                      </button>
                      <button
                        onClick={handleFinalize}
                        className="btn btn-primary"
                        style={{ height: '40px', flex: 1 }}
                        disabled={imageCount < 8 || isFinalizing}
                      >
                        {isFinalizing ? 'Đang phân tích...' : 'Hoàn tất đăng ký'}
                      </button>
                      <button onClick={handleCancel} className="btn btn-danger" style={{ height: '40px' }}>
                        Xóa tạm
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Instruction box */}
            <div style={{ backgroundColor: 'var(--surface-raised)', borderRadius: '8px', padding: '1rem', display: 'flex', gap: '0.75rem', fontSize: '0.85rem' }}>
              <Info size={18} style={{ color: 'var(--primary)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Tiêu chuẩn đăng ký khuôn mặt:</p>
                <p style={{ color: 'var(--text-muted)' }}>
                  Yêu cầu chụp ít nhất <strong style={{ color: 'var(--text-primary)' }}>8 ảnh chất lượng cao</strong>.
                  Sinh viên cần nhìn thẳng vào camera, đảm bảo ánh sáng đều, không đeo kính râm hoặc khẩu trang.
                  Hệ thống Haar Cascade phía native sẽ tự động lọc ảnh mờ hoặc ảnh chụp quá nhiều người.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
