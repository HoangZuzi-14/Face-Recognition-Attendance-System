"""Service for class management operations."""

from repositories.class_repository import ClassRepository


class ClassService:
    def __init__(self, repo=None):
        self._repo = repo or ClassRepository()

    def create_class(self, class_name):
        """Create a new class. Returns class_id or None."""
        name = str(class_name).strip()
        if not name:
            return None
        return self._repo.create_class(name)

    def get_classes(self):
        return self._repo.get_classes()

    def ensure_default_class(self):
        return self._repo.ensure_default_class()

    def class_has_roster(self, class_id):
        return self._repo.class_has_roster(class_id)

    def get_class_roster(self, class_id):
        return self._repo.get_class_roster(class_id)

    def delete_class(self, class_id):
        self._repo.delete_class(class_id)
