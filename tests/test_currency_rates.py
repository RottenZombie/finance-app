from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from core.api import get_all_rates


class CurrencyRateTests(unittest.TestCase):
    @patch("core.api.requests.get")
    def test_supported_exchange_rates_are_converted_to_try(self, get):
        response = Mock()
        response.json.return_value = {
            "result": "success",
            "rates": {"TRY": 35.0, "EUR": 0.92, "HUF": 360.0, "CHF": 0.88, "CZK": 22.5},
        }
        get.return_value = response
        result = get_all_rates()
        self.assertEqual(result["USD"], 35.0)
        self.assertEqual(result["EUR"], 35.0 / 0.92)
        self.assertEqual(result["HUF"], 35.0 / 360.0)
        self.assertEqual(result["CHF"], 35.0 / 0.88)
        self.assertEqual(result["CZK"], 35.0 / 22.5)
        self.assertEqual(result["TRY"], 1.0)
        self.assertEqual(result["status"], "Online")

    @patch("core.api.requests.get", side_effect=RuntimeError("offline"))
    def test_offline_response_keeps_expected_keys(self, _get):
        result = get_all_rates()
        self.assertIsNone(result["CHF"])
        self.assertIsNone(result["CZK"])
        self.assertEqual(result["TRY"], 1.0)
        self.assertEqual(result["status"], "Offline")


if __name__ == "__main__":
    unittest.main()
