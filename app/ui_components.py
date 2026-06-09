import streamlit as st
import textwrap

def inject_custom_css():
    """Reads style.css from assets and injects it into Streamlit."""
    import os
    css_path = os.path.join("assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def render_navbar():
    """Renders the top navigation bar."""
    st.markdown("""
<div class="zuzo-nav">
    <div style="display:flex;align-items:center;gap:2rem;">
        <span class="brand"><span class="brand-mark">✣</span> ZuzoNKT</span>
        <div class="nav-links">
            <a href="#">Điểm danh</a>
            <a href="#">Lớp học</a>
            <a href="#">Giám sát</a>
        </div>
    </div>
    <div class="nav-status">Face Attendance</div>
</div>
<div style="height:56px;"></div>
""", unsafe_allow_html=True)

def render_tabs():
    """Renders the top tabs."""
    st.markdown("""
<div class="zuzo-tabs">
    <span class="tab active">Console</span>
    <span class="tab">Roster</span>
    <span class="tab">Recognition</span>
    <span class="tab">Audit</span>
</div>
""", unsafe_allow_html=True)

def render_footer():
    """Renders the horizontal 3-column footer."""
    st.markdown("""
<div class="zuzo-footer">
    <div style="display: flex; justify-content: space-between; align-items: flex-end; width: 100%; text-align: left;">
        <div style="flex: 1;">
            <div class="footer-brand" style="margin-bottom: 1px;">Đại học Bách Khoa Hà Nội</div>
            <div style="font-size: 0.8rem; color: #5b403c; line-height: 1.2;">Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội</div>
        </div>
        <div style="flex: 1;"></div>
        <div style="flex: 1; text-align: right;">
            <div style="font-size: 0.8rem; color: #5b403c;">© 2026 HUST. All rights reserved.</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

def render_attendance_html(df):
    """Render attendance DataFrame as styled HTML table."""
    if df.empty:
        return '<p style="text-align:center;color:var(--on-surface-variant);padding:2rem;">Chưa có sinh viên trong lớp. Upload danh sách bên trái.</p>'

    badge_map = {
        "PRESENT": "badge-present",
        "LATE": "badge-late",
        "ABSENT": "badge-absent",
        "UNKNOWN": "badge-unknown",
        "NEED_REVIEW": "badge-review",
    }
    label_map = {
        "PRESENT": "Present",
        "LATE": "Late",
        "ABSENT": "Absent",
        "UNKNOWN": "Unknown",
        "NEED_REVIEW": "Review",
    }

    rows_list = []
    for _, row in df.iterrows():
        status = row["Trạng Thái"]
        badge_cls = badge_map.get(status, "badge-unknown")
        label = label_map.get(status, status)
        time_val = row["Thời Gian"]

        row_html = (
            f"<tr>"
            f"<td>{row['MSSV']}</td>"
            f"<td>{row['Họ và Tên']}</td>"
            f"<td>{time_val}</td>"
            f"<td><span class='badge {badge_cls}'>{label}</span></td>"
            f"</tr>"
        )
        rows_list.append(row_html)
        
    rows_joined = "".join(rows_list)
    
    html_table = (
        f'<div class="zuzo-card" style="min-height:400px;">'
        f'<div style="overflow-x:auto;">'
        f'<table class="att-table">'
        f'<thead>'
        f'<tr><th>MSSV</th><th>Họ và Tên</th><th>Thời gian</th><th>Trạng thái</th></tr>'
        f'</thead>'
        f'<tbody>{rows_joined}</tbody>'
        f'</table>'
        f'</div>'
        f'</div>'
    )
    return html_table
