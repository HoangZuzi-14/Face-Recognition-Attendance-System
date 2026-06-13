import sys
import os
import io
import base64
import json
import subprocess
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Đảm bảo đường dẫn repo được import chính xác
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# Import services
from services.class_service import ClassService
from services.student_service import StudentService
from services.attendance_service import AttendanceService
from services.recognition_service import RecognitionService
from services.audit_service import AuditService

# Import authentication helpers
from app.auth import can_perform, PERMISSIONS
from app.user_store import authenticate_user, get_user_by_username
from app.integrity import validate_integrity
from app.database import get_connection, write_audit_log

# Import camera control modules
from app.native_camera import (
    get_native_camera_preflight,
    start_native_camera_session,
    stop_native_camera_session,
    sync_native_camera_state,
)
from app.native_capture import (
    start_native_capture_session,
    stop_native_capture_session,
    sync_native_capture_state,
)
from app.add_face import get_existing_count, finalize_face_registration, clear_person_data

app = FastAPI(title="Face Attendance API Adapter", version="1.0.0")

# Cấu hình CORS để frontend React kết nối được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong thực tế có thể giới hạn ở localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Global Process Registry (Đóng vai trò thay thế Streamlit session_state)
# -----------------------------------------------------------------------------
process_registry = {
    "native_camera_process": None,
    "native_camera_log_handle": None,
    "native_camera_log_path": None,
    "native_camera_preflight": None,
    "native_camera_error": None,
    "native_camera_command": None,
    "run": False,
    
    "native_capture_process": None,
    "native_capture_person_key": None,
    "native_capture_command": None,
    "capture_mode": False
}

# Khởi tạo các Service instance toàn cục
class_service = ClassService()
student_service = StudentService()
attendance_service = AttendanceService()
recognition_service = RecognitionService()
audit_service = AuditService()

# -----------------------------------------------------------------------------
# Auth Token Helpers
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

def encode_token(user_data: dict) -> str:
    return base64.b64encode(json.dumps(user_data).encode()).decode()

def decode_token(token: str) -> Optional[dict]:
    try:
        return json.loads(base64.b64decode(token.encode()).decode())
    except:
        return None

def get_current_user(
    response: Response, 
    authorization: Optional[str] = Header(None), 
    token: Optional[str] = Query(None)
) -> dict:
    # Hỗ trợ lấy token từ Header (Authorization) hoặc query param (token)
    print(f"DEBUG AUTH - authorization header: {authorization}, query token: {token}")
    active_token = None
    if authorization:
        if authorization.startswith("Bearer "):
            active_token = authorization[7:]
        else:
            active_token = authorization
    elif token:
        active_token = token
            
    print(f"DEBUG AUTH - active_token: {active_token}")
    if not active_token:
        print("DEBUG AUTH - active_token is empty. Returning 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu Token xác thực."
        )
        
    user = decode_token(active_token)
    print(f"DEBUG AUTH - decoded user: {user}")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn."
        )
    return user

# Helper kiểm tra phân quyền
def check_permission(user: dict, required_permission: str):
    role = user.get("role")
    if not role or not can_perform(role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn không có quyền thực hiện thao tác này."
        )

# -----------------------------------------------------------------------------
# 1. AUTHENTICATION ENDPOINTS
# -----------------------------------------------------------------------------
@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    try:
        user = authenticate_user(payload.username, payload.password)
    except RuntimeError as e:
        # Lỗi thiếu bcrypt
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa."
        )
        
    # Lấy danh sách permission
    role = user["role"]
    permissions = list(PERMISSIONS.get(role, set()))
    
    # Tạo token đơn giản
    token = encode_token(user)
    
    return {
        "user": user,
        "permissions": permissions,
        "token": token
    }

@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    return {"ok": True}

@app.get("/api/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    role = current_user["role"]
    permissions = list(PERMISSIONS.get(role, set()))
    return {
        "user": current_user,
        "permissions": permissions
    }

# -----------------------------------------------------------------------------
# 2. CLASS MANAGEMENT ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/classes")
async def get_classes(current_user: dict = Depends(get_current_user)):
    try:
        classes_df = class_service.get_classes()
        result = classes_df.to_dict(orient="records")
        return {"classes": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu SQLite: {str(e)}"
        )

@app.post("/api/classes")
async def create_class(payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "class.delete")  # Chức năng quản trị lớp
    class_name = payload.get("class_name", "").strip()
    if not class_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên lớp học không được để trống."
        )
    
    # Kiểm tra trùng tên
    classes_df = class_service.get_classes()
    classes = classes_df.to_dict(orient="records")
    for c in classes:
        name = c["class_name"]
        if name.lower() == class_name.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tên lớp học đã tồn tại."
            )
            
    class_id = class_service.create_class(class_name)
    if not class_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tạo lớp học thất bại."
        )
    return {"id": class_id, "class_name": class_name}

@app.delete("/api/classes/{class_id}")
async def delete_class(class_id: int, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "class.delete")
    try:
        class_service.delete_class(class_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xóa lớp: {str(e)}"
        )

@app.get("/api/classes/{class_id}/summary")
async def get_class_summary(class_id: int, current_user: dict = Depends(get_current_user)):
    classes_df = class_service.get_classes()
    classes = classes_df.to_dict(orient="records")
    target_class = None
    for c in classes:
        if c["id"] == class_id:
            target_class = c
            break
            
    if not target_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lớp học không tồn tại."
        )
        
    class_name = target_class["class_name"]
    
    try:
        roster_df = class_service.get_class_roster(class_id)
        roster = roster_df.to_dict(orient="records")
        roster_count = len(roster)
        registered_count = sum(1 for r in roster if r.get("db_key") and str(r.get("db_key")).strip())
        has_roster = class_service.class_has_roster(class_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
    return {
        "id": class_id,
        "class_name": class_name,
        "roster_count": roster_count,
        "registered_count": registered_count,
        "has_roster": has_roster
    }

# -----------------------------------------------------------------------------
# 3. ROSTER MANAGEMENT ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/classes/{class_id}/roster")
async def get_class_roster(class_id: int, current_user: dict = Depends(get_current_user)):
    try:
        roster_df = class_service.get_class_roster(class_id)
        roster = roster_df.to_dict(orient="records")
        students = []
        for r in roster:
            students.append({
                "mssv": r.get("mssv"),
                "full_name": r.get("full_name"),
                "db_key": r.get("db_key")
            })
        return {"students": students}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/roster/template.csv")
async def get_roster_template(current_user: dict = Depends(get_current_user)):
    csv_content = "MSSV,FullName\nDEMO001,Nguyen Van A\nDEMO002,Tran Thi B\n"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=roster_template.csv"}
    )

@app.post("/api/classes/{class_id}/roster/default")
async def apply_default_roster(class_id: int, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "roster.import")
    from src.recognize import load_db
    try:
        db = load_db()
        existing_faces = list(db.keys()) if db else None
        res = student_service.ensure_default_roster(class_id, existing_faces)
        return {"added": res.get("added", 0), "skipped": res.get("skipped", 0)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi áp dụng danh sách mặc định: {str(e)}"
        )

@app.post("/api/classes/{class_id}/roster/import")
async def import_roster(class_id: int, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "roster.import")
    contents = await file.read()
    
    try:
        import pandas as pd
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Định dạng file không được hỗ trợ. Chỉ nhận .csv hoặc .xlsx"
            )
            
        # Validate DataFrame
        validation = student_service.validate_roster_dataframe(df)
        if not validation.get("valid", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation.get("message", "File danh sách không hợp lệ.")
            )
            
        from src.recognize import load_db
        db = load_db()
        existing_faces = list(db.keys()) if db else None
        
        res = student_service.upload_roster(class_id, df, existing_faces)
        return {"added": res.get("added", 0), "skipped": res.get("skipped", 0)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi đọc và lưu file danh sách: {str(e)}"
        )

# -----------------------------------------------------------------------------
# 4. STUDENT & FACE LINKING ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/students")
async def get_students(face: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    try:
        all_students_df = student_service.get_all_students()
        all_students = all_students_df.to_dict(orient="records")
        result = []
        for s in all_students:
            db_key = s.get("db_key")
            if face == "missing" and db_key and str(db_key).strip():
                continue
                
            result.append({
                "id": s.get("id"),
                "mssv": s.get("mssv"),
                "full_name": s.get("full_name"),
                "db_key": db_key
            })
        return {"students": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/students/{mssv}/face-link")
async def face_link(mssv: str, payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "face.register")
    db_key = payload.get("db_key", "").strip()
    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Face DB key không được trống."
        )
        
    try:
        student_service.link_student_face(mssv, db_key)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/classes/{class_id}/students")
async def ensure_student_in_class(class_id: int, payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "face.register")
    full_name = payload.get("full_name", "").strip()
    db_key = payload.get("db_key", "").strip()
    mssv = payload.get("mssv", "").strip() or None
    
    if not full_name or not db_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu Tên sinh viên hoặc Face DB key."
        )
        
    try:
        sid = student_service.ensure_student_in_class(class_id, full_name, db_key, mssv)
        return {"student_id": sid}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# -----------------------------------------------------------------------------
# 5. CAMERA & ATTENDANCE RUN ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/classes/{class_id}/camera/preflight")
async def get_camera_preflight(class_id: int, current_user: dict = Depends(get_current_user)):
    try:
        res = get_native_camera_preflight(class_id=class_id)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/classes/{class_id}/camera/start")
async def start_camera(class_id: int, payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "attendance.run")
    
    # Kiểm tra xem có đang chạy đăng ký khuôn mặt không
    if process_registry["capture_mode"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể khởi động camera điểm danh trong khi đang đăng ký khuôn mặt."
        )
        
    camera_index = int(payload.get("camera_index", 0))
    deadline_hour = int(payload.get("deadline_hour", 8))
    deadline_minute = int(payload.get("deadline_minute", 0))
    profile = payload.get("profile", "default")
    
    # Kiểm tra Roster và Embeddings
    preflight = get_native_camera_preflight(class_id=class_id)
    if preflight["active_identity_count"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lớp học chưa có sinh viên nào đăng ký khuôn mặt hoạt động."
        )
        
    # Reset trackers và xóa kết quả điểm danh cũ của ngày hôm nay trước khi chạy mới
    from src.recognize import reset_trackers
    try:
        attendance_service.clear_today(class_id)
        reset_trackers()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi reset trạng thái điểm danh: {str(e)}"
        )
        
    # Khởi động session
    try:
        start_native_camera_session(
            process_registry,
            camera_index=camera_index,
            class_id=class_id,
            deadline_hour=deadline_hour,
            deadline_minute=deadline_minute,
            profile=profile
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khởi chạy camera native: {str(e)}"
        )
        
    return {
        "running": process_registry["run"],
        "log_path": process_registry["native_camera_log_path"],
        "command": process_registry["native_camera_command"]
    }

@app.post("/api/camera/stop")
async def stop_camera(current_user: dict = Depends(get_current_user)):
    # Phải có quyền điểm danh
    check_permission(current_user, "attendance.run")
    stopped = stop_native_camera_session(process_registry)
    return {"running": process_registry["run"], "stopped": stopped}

@app.get("/api/camera/status")
async def get_camera_status():
    sync_native_camera_state(process_registry)
    return {
        "running": process_registry["run"],
        "error": process_registry.get("native_camera_error"),
        "log_path": process_registry.get("native_camera_log_path")
    }

@app.get("/api/classes/{class_id}/attendance/today")
async def get_today_attendance(class_id: int, deadline_hour: int = 8, deadline_minute: int = 0, current_user: dict = Depends(get_current_user)):
    try:
        df = attendance_service.get_full_attendance(class_id, deadline_hour, deadline_minute)
        rows = df.to_dict(orient="records")
        
        # Mapping các trường tiếng Việt sang tiếng Anh
        formatted_rows = []
        summary = {"present": 0, "late": 0, "absent": 0, "unknown": 0, "total": 0}
        
        for r in rows:
            status_val = r.get("Trạng Thái", "ABSENT")
            formatted_rows.append({
                "mssv": r.get("MSSV"),
                "full_name": r.get("Họ và Tên"),
                "time": r.get("Thời Gian"),
                "status": status_val
            })
            
            # Cập nhật summary
            summary["total"] += 1
            if status_val == "PRESENT":
                summary["present"] += 1
            elif status_val == "LATE":
                summary["late"] += 1
            elif status_val == "ABSENT":
                summary["absent"] += 1
            elif status_val == "UNKNOWN":
                summary["unknown"] += 1
                
        return {"rows": formatted_rows, "summary": summary}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/classes/{class_id}/attendance/clear-today")
async def clear_today_attendance(class_id: int, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "attendance.clear")
    try:
        attendance_service.clear_today(class_id)
        from src.recognize import reset_trackers
        reset_trackers()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/classes/{class_id}/attendance/export.csv")
async def export_attendance_csv(class_id: int, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "report.export")
    export_dir = Path("reports")
    export_dir.mkdir(exist_ok=True)
    export_path = export_dir / f"attendance_class_{class_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    try:
        attendance_service.export_csv(class_id, str(export_path))
        return FileResponse(
            path=str(export_path),
            filename=export_path.name,
            media_type="text/csv"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xuất CSV: {str(e)}"
        )

# -----------------------------------------------------------------------------
# 6. FACE ENROLLMENT ENDPOINTS (QUẢN LÝ TIẾN TRÌNH CAMERA NATIVE CHỤP ẢNH)
# -----------------------------------------------------------------------------
@app.post("/api/faces/enroll/start")
async def start_enrollment(payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "face.register")
    
    if process_registry["run"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể khởi động camera chụp đăng ký khi đang chạy camera điểm danh."
        )
        
    person_key = payload.get("person_key", "").strip()
    camera_index = int(payload.get("camera_index", 0))
    profile = payload.get("profile", "default")
    start_index = int(payload.get("start_index", 0))
    
    if not person_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu Person Key đăng ký."
        )
        
    process_registry["capture_mode"] = True
    
    try:
        start_native_capture_session(
            process_registry,
            camera_index=camera_index,
            person_key=person_key,
            start_index=start_index,
            profile=profile
        )
    except Exception as e:
        process_registry["capture_mode"] = False
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khởi chạy native capture: {str(e)}"
        )
        
    return {
        "running": True,
        "person_key": person_key,
        "start_index": start_index
    }

@app.get("/api/faces/enroll/status")
async def get_enrollment_status(person_key: str):
    running = sync_native_capture_state(process_registry)
    try:
        image_count = get_existing_count(person_key)
    except Exception:
        image_count = 0
        
    return {
        "running": running,
        "person_key": person_key,
        "image_count": image_count,
        "valid_count": image_count
    }

@app.post("/api/faces/enroll/restart")
async def restart_enrollment(payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "face.register")
    person_key = payload.get("person_key", "").strip()
    camera_index = int(payload.get("camera_index", 0))
    start_index = int(payload.get("start_index", 0))
    
    try:
        start_native_capture_session(
            process_registry,
            camera_index=camera_index,
            person_key=person_key,
            start_index=start_index
        )
        return {"running": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/faces/enroll/finalize")
async def finalize_enrollment(payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "face.register")
    person_key = payload.get("person_key", "").strip()
    start_index = int(payload.get("start_index", 0))
    
    # Kiểm tra số lượng ảnh tối thiểu
    try:
        img_count = get_existing_count(person_key)
    except Exception:
        img_count = 0
        
    if img_count < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có {img_count} ảnh đã chụp. Cần tối thiểu 8 ảnh hợp lệ."
        )
        
    # Tắt tiến trình chụp trước
    stop_native_capture_session(process_registry)
    process_registry["capture_mode"] = False
    
    # Tiến hành finalize (tiền xử lý + trích xuất embedding + lưu pkl)
    try:
        res = finalize_face_registration(person_key, start_index)
        
        # Reload Face DB
        from src.recognize import reload_db, reset_trackers
        reload_db()
        reset_trackers()
        
        return {
            "ok": res.ok,
            "stage": res.stage,
            "message": res.message,
            "valid_images": res.valid_images
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi tiền xử lý và trích xuất embedding: {str(e)}"
        )

@app.post("/api/faces/enroll/cancel")
async def cancel_enrollment(payload: dict, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "face.register")
    person_key = payload.get("person_key", "").strip()
    
    stop_native_capture_session(process_registry)
    process_registry["capture_mode"] = False
    
    try:
        clear_person_data(person_key)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi dọn dẹp dữ liệu raw: {str(e)}"
        )

# -----------------------------------------------------------------------------
# 7. DIAGNOSTICS & SYSTEM ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/recognition/stats")
async def get_recognition_stats(class_id: Optional[int] = None, limit: int = 50, current_user: dict = Depends(get_current_user)):
    try:
        df = attendance_service.get_recognition_stats(class_id, limit)
        return {"rows": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/recognition/events")
async def get_recognition_events(class_id: Optional[int] = None, limit: int = 100, current_user: dict = Depends(get_current_user)):
    # Lấy dữ liệu raw sự kiện nhận diện từ SQLite DB
    conn = get_connection()
    try:
        if class_id:
            query = """
                SELECT id, class_id, student_db_key, decision, confidence, distance, gap, 
                       created_at, liveness_score, liveness_label, attack_type, attendance_logged,
                       live_score, print_score, replay_score, spoof_score
                FROM recognition_events
                WHERE class_id = ?
                ORDER BY created_at DESC LIMIT ?
            """
            cursor = conn.execute(query, (class_id, limit))
        else:
            query = """
                SELECT id, class_id, student_db_key, decision, confidence, distance, gap, 
                       created_at, liveness_score, liveness_label, attack_type, attendance_logged,
                       live_score, print_score, replay_score, spoof_score
                FROM recognition_events
                ORDER BY created_at DESC LIMIT ?
            """
            cursor = conn.execute(query, (limit,))
            
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Convert true/false boolean
        for r in rows:
            r["attendance_logged"] = bool(r["attendance_logged"])
            
        return {"rows": rows}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        conn.close()

@app.get("/api/audit/logs")
async def get_audit_logs(limit: int = 50, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "system.monitor")
    try:
        df = audit_service.get_recent_logs(limit)
        return {"rows": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/integrity/check")
async def check_integrity(current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "system.monitor")
    try:
        report = validate_integrity()
        return {
            "ok": report.ok,
            "students_missing_face_embeddings": report.students_missing_face_embeddings,
            "face_embeddings_missing_students": report.face_embeddings_missing_students,
            "missing_raw_dirs": report.missing_raw_dirs,
            "missing_processed_dirs": report.missing_processed_dirs,
            "attendance_keys_missing_students": report.attendance_keys_missing_students,
            "errors": report.errors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# API endpoint giả lập để đáp ứng API contract nhưng backend chưa có
@app.get("/api/camera/hud")
async def get_camera_hud():
    # HUD details are strictly handled in subprocess memory; return 501 Not Implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="HUD telemetry is local in subprocess memory; browser HUD is not supported."
    )
