import pytest

from plugins.emu.app.parsers.vssadmin_shadow import Parser


@pytest.fixture
def dummy_blob():
    return r"""
vssadmin 1.1 - Volume Shadow Copy Service administrative command-line tool
(C) Copyright 2001-2013 Microsoft Corp.

Successfully created shadow copy for 'C:\'
    Shadow Copy ID: {uuid}
    Shadow Copy Volume Name: \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy7
"""


class TestVssadminShadowParser:
    def test_parse_blob(self, dummy_blob):
        results = Parser._get_volume_name(dummy_blob)
        assert results == r'\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy7'

    def test_parse_blob_without_match(self):
        assert not Parser._get_volume_name('no volume name here')
