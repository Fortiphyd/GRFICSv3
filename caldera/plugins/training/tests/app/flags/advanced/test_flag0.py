import pytest

from plugins.training.app.flags.advanced.flag_0 import AdvancedFlag0


class TestFlag:
    def test_valid_external_http_contact(self):
        test_contact = 'http://10.10.10.10:8888'
        assert AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_valid_external_https_contact(self):
        test_contact = 'https://10.10.10.10:8888'
        assert AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_valid_external_http_contact_no_port(self):
        test_contact = 'http://10.10.10.10'
        assert AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_valid_external_https_contact_no_port(self):
        test_contact = 'https://10.10.10.10'
        assert AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_internal_http_contact_loopback(self):
        test_contact = 'http://127.0.0.1:8888'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_internal_http_contact_loopback_no_port(self):
        test_contact = 'http://127.0.0.1'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_internal_https_contact_loopback(self):
        test_contact = 'https://127.0.0.1:12345'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_internal_http_contact_loopback_other(self):
        test_contact = 'http://127.10.10.10'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_internal_http_contact_0000(self):
        test_contact = 'http://0.0.0.0:8888'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_internal_http_contact_0000_no_port(self):
        test_contact = 'http://0.0.0.0'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_invalid_port(self):
        test_contact = 'http://10.10.10.10:abcd'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_out_of_range_port(self):
        test_contact = 'http://10.10.10.10:123456'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_not_ip_addr(self):
        test_contact = 'http://myhostname.tld:1234'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)

    def test_wrong_protocol(self):
        test_contact = 'nothttp://10.10.10.10:12345'
        assert not AdvancedFlag0.valid_external_http_contact(test_contact)
