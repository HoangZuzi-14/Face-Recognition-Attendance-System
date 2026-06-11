import os
import sys
import unittest


class StreamlitPathSetupTests(unittest.TestCase):
    def test_repo_root_is_promoted_before_app_directory(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        app_dir = os.path.join(repo_root, "app")
        script_path = os.path.join(app_dir, "main.py")
        fake_sys_path = [app_dir, "placeholder", repo_root]

        from app.path_setup import ensure_repo_root_first

        result = ensure_repo_root_first(script_path, path_list=fake_sys_path)

        self.assertEqual(result, repo_root)
        self.assertEqual(fake_sys_path[0], repo_root)
        self.assertEqual(fake_sys_path.count(repo_root), 1)
        self.assertIn(app_dir, fake_sys_path)

    def test_import_services_resolves_legacy_package_after_path_setup(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        app_dir = os.path.join(repo_root, "app")

        original_path = list(sys.path)
        original_modules = {
            name: module
            for name, module in sys.modules.items()
            if name == "services" or name.startswith("services.")
        }
        for name in list(original_modules):
            sys.modules.pop(name, None)

        try:
            sys.path[:] = [app_dir, repo_root] + [
                path for path in original_path if path not in {app_dir, repo_root}
            ]

            from app.path_setup import ensure_repo_root_first

            ensure_repo_root_first(os.path.join(app_dir, "main.py"))

            import services.class_service as class_service

            self.assertEqual(
                os.path.abspath(class_service.__file__),
                os.path.join(repo_root, "services", "class_service.py"),
            )
        finally:
            sys.path[:] = original_path
            for name in list(sys.modules):
                if name == "services" or name.startswith("services."):
                    sys.modules.pop(name, None)
            sys.modules.update(original_modules)


if __name__ == "__main__":
    unittest.main()
