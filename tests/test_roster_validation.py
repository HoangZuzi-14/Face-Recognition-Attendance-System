import unittest

import pandas as pd


class RosterValidationTests(unittest.TestCase):
    def test_validate_roster_requires_mssv_and_name_column(self):
        from app.database import validate_roster_dataframe

        valid, message = validate_roster_dataframe(pd.DataFrame({"FullName": ["A"]}))
        self.assertFalse(valid)
        self.assertIn("MSSV", message)

        valid, message = validate_roster_dataframe(pd.DataFrame({"MSSV": ["S1"]}))
        self.assertFalse(valid)
        self.assertIn("FullName", message)

        valid, message = validate_roster_dataframe(
            pd.DataFrame({"MSSV": ["S1"], "FullName": ["A"]})
        )
        self.assertTrue(valid)
        self.assertEqual(message, "OK")


if __name__ == "__main__":
    unittest.main()
