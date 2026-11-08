import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from checker import check_public_url, CheckError


class PublicUrlTests(unittest.TestCase):
    def test_rejects_local_ip(self):
        with self.assertRaises(CheckError):
            check_public_url("https://127.0.0.1/")

    def test_rejects_http(self):
        with self.assertRaises(CheckError):
            check_public_url("http://example.com")

    def test_rejects_nonstandard_port(self):
        with self.assertRaises(CheckError):
            check_public_url("https://example.com:8000")

    def test_rejects_local_domain(self):
        with self.assertRaises(CheckError):
            check_public_url("https://test.local/")

    @mock.patch("checker.socket.getaddrinfo")
    def test_accepts_public_domain(self, mock_dns):
        mock_dns.return_value = [(None,None,None,None,("93.184.215.14",443))]
        self.assertEqual(check_public_url("https://example.com"), "https://example.com")

    @mock.patch("checker.socket.getaddrinfo")
    def test_rejects_private_dns(self, mock_dns):
        mock_dns.return_value = [(None,None,None,None,("10.0.0.1",443))]
        with self.assertRaises(CheckError):
            check_public_url("https://example.com")


if __name__ == "__main__":
    unittest.main()
