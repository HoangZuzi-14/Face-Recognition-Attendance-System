ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_VIEWER = "viewer"

PERMISSIONS = {
    ROLE_ADMIN: {
        "attendance.run",
        "attendance.clear",
        "class.delete",
        "roster.import",
        "face.register",
        "report.export",
        "system.monitor",
    },
    ROLE_TEACHER: {
        "attendance.run",
        "face.register",
        "report.export",
        "system.monitor",
    },
    ROLE_VIEWER: {
        "system.monitor",
    },
}


def can_perform(role, permission):
    return permission in PERMISSIONS.get(role, set())
