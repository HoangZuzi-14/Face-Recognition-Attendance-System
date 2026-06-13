"""Role-specific portal configuration for the Streamlit shell."""

from app.auth import ROLE_ADMIN, ROLE_TEACHER


_PORTALS = {
    ROLE_ADMIN: {
        "label": "Admin Portal",
        "description": "Full system administration",
        "tabs": ("setup", "roster", "face"),
        "tab_labels": ("Lop hoc", "Danh sach", "Khuon mat"),
    },
    ROLE_TEACHER: {
        "label": "Teacher Portal",
        "description": "Attendance and class operations",
        "tabs": ("roster", "face"),
        "tab_labels": ("Danh sach", "Khuon mat"),
    },
}


def portal_for_role(role):
    portal = _PORTALS.get(role, _PORTALS[ROLE_TEACHER])
    return {
        "label": portal["label"],
        "description": portal["description"],
        "tabs": tuple(portal["tabs"]),
        "tab_labels": tuple(portal["tab_labels"]),
    }
