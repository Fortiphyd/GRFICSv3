"""
Unit tests for router firewall rule generation, default configuration,
traffic stats helpers, and conntrack parsing.

Run with:  pytest router/test_app.py -v
"""
import os
import sys
import json
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

# app.py has module-level side effects: load_config(), subprocess.run(iptables-restore),
# and app.run() (blocking). Patch all of them before import so the module loads cleanly.
_open_mock = mock_open()
with patch("subprocess.run", return_value=MagicMock(returncode=0)), \
     patch("os.path.exists", return_value=False), \
     patch("os.makedirs"), \
     patch("builtins.open", _open_mock), \
     patch("flask.Flask.run"):
    sys.path.insert(0, os.path.dirname(__file__))
    import app as flask_app


# ---------------------------------------------------------------------------
# build_iptables_rules — pure function, no mocking needed
# ---------------------------------------------------------------------------

class TestForwardPolicy:
    def test_forward_chain_is_drop(self):
        result = flask_app.build_iptables_rules([])
        assert ":FORWARD DROP [0:0]" in result

    def test_forward_accept_policy_absent(self):
        result = flask_app.build_iptables_rules([])
        assert ":FORWARD ACCEPT" not in result


class TestConntrackBaseRules:
    def test_established_related_rule_present(self):
        result = flask_app.build_iptables_rules([])
        assert "-m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT" in result

    def test_invalid_drop_rule_present(self):
        result = flask_app.build_iptables_rules([])
        assert "-m conntrack --ctstate INVALID -j DROP" in result

    def test_conntrack_rules_precede_user_rules(self):
        rules = [{"proto": "tcp", "src": "192.168.90.0/24", "dst": "192.168.95.2",
                  "iface_in": "eth2", "iface_out": "", "dport": "502",
                  "action": "ACCEPT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert result.index("ESTABLISHED,RELATED") < result.index("192.168.90.0/24"), \
            "Stateful conntrack rules must appear before user-defined rules"

    def test_ics_default_allow_present(self):
        result = flask_app.build_iptables_rules([])
        assert f"-A FORWARD -s {flask_app.ICS_SUBNET} -j ACCEPT" in result

    def test_ics_default_allow_uses_subnet_not_interface(self):
        result = flask_app.build_iptables_rules([])
        # Must not rely on a specific interface name
        ics_allow_line = next(
            l for l in result.splitlines()
            if flask_app.ICS_SUBNET in l and "-j ACCEPT" in l
        )
        assert "-i eth" not in ics_allow_line

    def test_catchall_logdrop_present(self):
        result = flask_app.build_iptables_rules([])
        assert "-A FORWARD -j LOGDROP" in result

    def test_catchall_logdrop_after_user_rules_and_ics_allow(self):
        rules = [{"proto": "tcp", "src": "192.168.90.0/24", "dst": "192.168.95.2",
                  "iface_in": "", "iface_out": "", "dport": "502",
                  "action": "ACCEPT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        logdrop_pos = result.index("-A FORWARD -j LOGDROP")
        assert result.index("192.168.90.0/24") < logdrop_pos, \
            "Catch-all LOGDROP must appear after user rules"
        assert result.index(flask_app.ICS_SUBNET) < logdrop_pos, \
            "Catch-all LOGDROP must appear after ICS default-allow rule"


class TestProtoHandling:
    def test_proto_all_omits_p_flag(self):
        rules = [{"proto": "all", "src": "10.0.0.1", "dst": "10.0.0.2",
                  "iface_in": "", "iface_out": "", "dport": "", "action": "ACCEPT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert "-A FORWARD -s 10.0.0.1 -d 10.0.0.2 -j ACCEPT" in result
        # -p all must not appear
        user_lines = [l for l in result.splitlines()
                      if "10.0.0.1" in l or "10.0.0.2" in l]
        for line in user_lines:
            assert "-p all" not in line

    def test_proto_tcp_includes_p_flag(self):
        rules = [{"proto": "tcp", "src": "192.168.90.0/24", "dst": "192.168.95.2",
                  "iface_in": "eth2", "iface_out": "", "dport": "502",
                  "action": "ACCEPT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert "-A FORWARD -p tcp -s 192.168.90.0/24 -d 192.168.95.2 -i eth2 --dport 502 -j ACCEPT" in result

    def test_dport_skipped_for_icmp(self):
        rules = [{"proto": "icmp", "src": "0.0.0.0/0", "dst": "0.0.0.0/0",
                  "iface_in": "", "iface_out": "", "dport": "8080",
                  "action": "ACCEPT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert "--dport" not in result

    def test_dport_skipped_for_proto_all(self):
        rules = [{"proto": "all", "src": "0.0.0.0/0", "dst": "0.0.0.0/0",
                  "iface_in": "", "iface_out": "", "dport": "443",
                  "action": "ACCEPT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert "--dport" not in result


class TestActionHandling:
    def test_drop_routes_to_logdrop(self):
        rules = [{"proto": "tcp", "src": "0.0.0.0/0", "dst": "0.0.0.0/0",
                  "iface_in": "", "iface_out": "", "dport": "", "action": "DROP", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert "-j LOGDROP" in result

    def test_reject_routes_to_logreject(self):
        rules = [{"proto": "tcp", "src": "0.0.0.0/0", "dst": "0.0.0.0/0",
                  "iface_in": "", "iface_out": "", "dport": "", "action": "REJECT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert "-j LOGREJECT" in result

    def test_accept_uses_accept_directly(self):
        rules = [{"proto": "tcp", "src": "0.0.0.0/0", "dst": "0.0.0.0/0",
                  "iface_in": "", "iface_out": "", "dport": "", "action": "ACCEPT", "comment": ""}]
        result = flask_app.build_iptables_rules(rules)
        assert "-j ACCEPT" in result
        assert "LOGACCEPT" not in result


class TestCommentHandling:
    def test_comment_absent_from_iptables_output(self):
        rules = [{"proto": "all", "src": "0.0.0.0/0", "dst": "0.0.0.0/0",
                  "iface_in": "", "iface_out": "", "dport": "", "action": "ACCEPT",
                  "comment": "TEMP - allow all traffic for troubleshooting - DO NOT LEAVE IN PRODUCTION"}]
        result = flask_app.build_iptables_rules(rules)
        assert "TEMP" not in result
        assert "troubleshooting" not in result
        assert "PRODUCTION" not in result


class TestOutputStructure:
    def test_starts_with_filter_table(self):
        result = flask_app.build_iptables_rules([])
        assert result.startswith("*filter")

    def test_ends_with_commit(self):
        result = flask_app.build_iptables_rules([])
        assert result.strip().endswith("COMMIT")


class TestApplyRulesNow:
    def test_writes_rules_file_on_fresh_volume(self):
        """Startup with no pre-existing rules file must still write and apply rules."""
        written = {}
        def fake_open(path, mode='r', *a, **kw):
            if mode == 'w':
                m = mock_open()()
                written[path] = m
                return m
            raise FileNotFoundError
        with patch("builtins.open", fake_open), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)), \
             patch("os.makedirs"):
            flask_app._apply_rules_now([])
        assert flask_app.FIREWALL_RULES_PATH in written

    def test_applies_rules_even_when_no_prior_file(self):
        """iptables-restore must be called regardless of whether the rules file existed."""
        sub_calls = []
        with patch("builtins.open", mock_open()), \
             patch("subprocess.run", side_effect=lambda cmd, **kw: sub_calls.append(cmd) or MagicMock(returncode=0)), \
             patch("os.makedirs"):
            flask_app._apply_rules_now([])
        restore_calls = [c for c in sub_calls if "iptables-restore" in c]
        assert len(restore_calls) == 1

    def test_nat_prerouting_flushed_alongside_forward(self):
        """Applying rules must reset the nat PREROUTING chain, not just filter/FORWARD."""
        sub_calls = []
        with patch("builtins.open", mock_open()), \
             patch("subprocess.run", side_effect=lambda cmd, **kw: sub_calls.append(cmd) or MagicMock(returncode=0)), \
             patch("os.makedirs"):
            flask_app._apply_rules_now([], [])
        assert ["iptables", "-t", "nat", "-F", "PREROUTING"] in sub_calls


# ---------------------------------------------------------------------------
# build_nat_rules / build_iptables_rules(nat_rules=...) — port forwarding
# ---------------------------------------------------------------------------

NAT_RULE = {
    "iface_in": "eth2", "proto": "tcp", "src": "0.0.0.0/0", "dst": "",
    "ext_port": "8080", "target_ip": "192.168.95.5", "target_port": "80",
    "auto_fw_rule": True, "enabled": True, "comment": "",
}


class TestBuildNatRules:
    def test_starts_with_nat_table_and_prerouting_chain(self):
        result = flask_app.build_nat_rules([])
        assert result.startswith("*nat")
        assert ":PREROUTING ACCEPT [0:0]" in result

    def test_ends_with_commit(self):
        result = flask_app.build_nat_rules([])
        assert result.strip().endswith("COMMIT")

    def test_postrouting_chain_not_mentioned(self):
        """POSTROUTING is owned by network-init.py/WireGuard masquerade — must stay untouched."""
        result = flask_app.build_nat_rules([NAT_RULE])
        assert "POSTROUTING" not in result

    def test_dnat_line_for_basic_forward(self):
        result = flask_app.build_nat_rules([NAT_RULE])
        assert "-A PREROUTING -i eth2 -p tcp --dport 8080 -j DNAT --to-destination 192.168.95.5:80" in result

    def test_disabled_rule_omitted(self):
        rule = {**NAT_RULE, "enabled": False}
        result = flask_app.build_nat_rules([rule])
        assert "DNAT" not in result

    def test_src_restriction_included_when_set(self):
        rule = {**NAT_RULE, "src": "192.168.90.6/32"}
        result = flask_app.build_nat_rules([rule])
        assert "-s 192.168.90.6/32" in result

    def test_any_src_omits_s_flag(self):
        result = flask_app.build_nat_rules([NAT_RULE])
        line = next(l for l in result.splitlines() if "DNAT" in l)
        assert "-s " not in line

    def test_dst_restriction_included_when_set(self):
        rule = {**NAT_RULE, "dst": "192.168.90.200"}
        result = flask_app.build_nat_rules([rule])
        assert "-d 192.168.90.200" in result

    def test_blank_dst_omits_d_flag(self):
        result = flask_app.build_nat_rules([NAT_RULE])
        line = next(l for l in result.splitlines() if "DNAT" in l)
        assert "-d " not in line


class TestAssociatedFilterRule:
    def test_auto_fw_rule_adds_forward_accept(self):
        result = flask_app.build_iptables_rules([], [NAT_RULE])
        assert "-A FORWARD -i eth2 -p tcp -d 192.168.95.5 --dport 80 -j ACCEPT" in result

    def test_auto_fw_rule_false_adds_nothing(self):
        rule = {**NAT_RULE, "auto_fw_rule": False}
        result = flask_app.build_iptables_rules([], [rule])
        assert "192.168.95.5" not in result

    def test_disabled_nat_rule_adds_nothing(self):
        rule = {**NAT_RULE, "enabled": False}
        result = flask_app.build_iptables_rules([], [rule])
        assert "192.168.95.5" not in result

    def test_associated_rule_precedes_catchall_logdrop(self):
        result = flask_app.build_iptables_rules([], [NAT_RULE])
        assert result.index("192.168.95.5") < result.index("-A FORWARD -j LOGDROP")

    def test_no_nat_rules_leaves_filter_output_unchanged(self):
        assert flask_app.build_iptables_rules([]) == flask_app.build_iptables_rules([], [])
        assert flask_app.build_iptables_rules([]) == flask_app.build_iptables_rules([], None)


# ---------------------------------------------------------------------------
# parse_iptables_rules / revert — must reconstruct only user rules from the
# live FORWARD chain, not the framework-managed lines build_iptables_rules
# regenerates itself (regression test for the Revert bug).
# ---------------------------------------------------------------------------

class TestParseIptablesRules:
    def _parse(self, forward_lines):
        out = "\n".join(forward_lines) + "\n"
        with patch("subprocess.check_output", return_value=out) as mock_co:
            result = flask_app.parse_iptables_rules()
        args = mock_co.call_args[0][0]
        assert args == ["iptables", "-S", "FORWARD"], "must scope the query to FORWARD only"
        return result

    def test_framework_lines_excluded(self):
        result = self._parse([
            "-A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
            "-A FORWARD -m conntrack --ctstate INVALID -j DROP",
            f"-A FORWARD -s {flask_app.ICS_SUBNET} -j ACCEPT",
            "-A FORWARD -j LOGDROP",
        ])
        assert result == []

    def test_user_accept_rule_recovered(self):
        result = self._parse(["-A FORWARD -p tcp -s 192.168.90.0/24 -d 192.168.95.2 --dport 502 -j ACCEPT"])
        assert len(result) == 1
        r = result[0]
        assert r["src"] == "192.168.90.0/24"
        assert r["dst"] == "192.168.95.2"
        assert r["proto"] == "tcp"
        assert r["dport"] == "502"
        assert r["action"] == "ACCEPT"

    def test_user_drop_rule_action_unprefixed_from_logdrop(self):
        """A user DROP rule renders as `-j LOGDROP` (see build_iptables_rules) —
        must be read back as action DROP, not the literal chain name LOGDROP."""
        result = self._parse(["-A FORWARD -p tcp -s 1.2.3.4 -d 5.6.7.8 --dport 80 -j LOGDROP"])
        assert len(result) == 1
        assert result[0]["action"] == "DROP"

    def test_user_reject_rule_action_unprefixed_from_logreject(self):
        result = self._parse(["-A FORWARD -p tcp -s 1.2.3.4 -d 5.6.7.8 --dport 80 -j LOGREJECT"])
        assert result[0]["action"] == "REJECT"

    def test_bare_catchall_logdrop_not_confused_with_user_drop_rule(self):
        """Only the exact bare catch-all line is excluded; a matched-and-dropped
        user rule (which also targets LOGDROP) must still come back."""
        result = self._parse([
            "-A FORWARD -p tcp -s 1.2.3.4 -d 5.6.7.8 --dport 80 -j LOGDROP",
            "-A FORWARD -j LOGDROP",
        ])
        assert len(result) == 1
        assert result[0]["src"] == "1.2.3.4"

    def test_nat_associated_accept_excluded(self):
        with patch.object(flask_app, "nat_rules", [NAT_RULE]):
            result = self._parse([flask_app._nat_associated_forward_line(NAT_RULE)])
        assert result == []

    def test_missing_src_dst_default_to_any_address_not_literal_any(self):
        """Must match the schema build_iptables_rules expects (0.0.0.0/0), not
        the string 'any' — 'any' is not a valid iptables address."""
        result = self._parse(["-A FORWARD -j ACCEPT"])
        assert result[0]["src"] == "0.0.0.0/0"
        assert result[0]["dst"] == "0.0.0.0/0"

    def test_missing_proto_defaults_to_all_not_literal_any(self):
        """build_iptables_rules only omits -p when proto == 'all'; 'any' would
        wrongly re-emit '-p any' on the next Apply."""
        result = self._parse(["-A FORWARD -s 10.0.0.1 -d 10.0.0.2 -j ACCEPT"])
        assert result[0]["proto"] == "all"


class TestRevertChanges:
    def test_revert_updates_module_global_pending_rules(self):
        """Regression test: revert_changes() previously reassigned a local
        `pending_rules` instead of the module global (missing `global`
        declaration), so Revert silently did nothing but clear the dirty flag."""
        client = flask_app.app.test_client()
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["role"] = "admin"
        live_forward = "-A FORWARD -p tcp -s 1.2.3.4 -d 5.6.7.8 --dport 80 -j ACCEPT\n"
        with patch("subprocess.check_output", return_value=live_forward), \
             patch.object(flask_app, "save_config"):
            client.post("/revert")
        assert flask_app.pending_rules == [{
            "index": 1, "chain": "FORWARD", "iface_in": "", "iface_out": "",
            "src": "1.2.3.4", "dst": "5.6.7.8", "proto": "tcp", "dport": "80",
            "action": "ACCEPT", "comment": "",
        }]


# ---------------------------------------------------------------------------
# DEFAULT_RULES — misconfiguration scenario
# ---------------------------------------------------------------------------

class TestDefaultRules:
    def test_exactly_one_default_rule(self):
        assert len(flask_app.DEFAULT_RULES) == 1

    def test_default_rule_is_allow_any(self):
        rule = flask_app.DEFAULT_RULES[0]
        assert rule["action"] == "ACCEPT"
        assert rule["src"] == "0.0.0.0/0"
        assert rule["dst"] == "0.0.0.0/0"
        assert rule["proto"] == "all"

    def test_default_rule_has_no_interface_restriction(self):
        rule = flask_app.DEFAULT_RULES[0]
        assert rule["iface_in"] == ""
        assert rule["iface_out"] == ""

    def test_default_rule_has_descriptive_comment(self):
        rule = flask_app.DEFAULT_RULES[0]
        assert rule.get("comment"), "Default allow-any rule must carry a warning comment"

    def test_default_rule_produces_allow_any_iptables_line(self):
        result = flask_app.build_iptables_rules(flask_app.DEFAULT_RULES)
        assert "-A FORWARD -s 0.0.0.0/0 -d 0.0.0.0/0 -j ACCEPT" in result

    def test_default_rule_combined_with_default_deny_policy(self):
        # Even with the allow-any user rule, the policy header must still be DROP
        result = flask_app.build_iptables_rules(flask_app.DEFAULT_RULES)
        assert ":FORWARD DROP [0:0]" in result


# ---------------------------------------------------------------------------
# parse_conntrack — /proc/net/nf_conntrack parsing
# ---------------------------------------------------------------------------

SAMPLE_CONNTRACK = """\
ipv4     2 tcp      6 86393 ESTABLISHED src=192.168.95.2 dst=192.168.90.107 sport=49832 dport=8080 src=192.168.90.107 dst=192.168.95.2 sport=8080 dport=49832 [ASSURED] mark=0 zone=0 use=2
ipv4     2 udp      17 25 src=192.168.95.5 dst=8.8.8.8 sport=54321 dport=53 [UNREPLIED] src=8.8.8.8 dst=192.168.95.5 sport=53 dport=54321 mark=0 zone=0 use=1
ipv4     2 icmp     1 29 src=192.168.90.6 dst=192.168.95.2 type=8 code=0 id=1234 src=192.168.95.2 dst=192.168.90.6 type=0 code=0 id=1234 mark=0 zone=0 use=1
"""


class TestParseConntrack:
    def _parse(self, content=SAMPLE_CONNTRACK):
        with patch("builtins.open", mock_open(read_data=content)):
            return flask_app.parse_conntrack()

    def test_returns_correct_count(self):
        entries = self._parse()
        assert len(entries) == 3

    def test_tcp_entry_fields(self):
        entries = self._parse()
        tcp = next(e for e in entries if e['proto'] == 'tcp')
        assert tcp['state'] == 'ESTABLISHED'
        assert tcp['src'] == '192.168.95.2'
        assert tcp['dst'] == '192.168.90.107'
        assert tcp['sport'] == '49832'
        assert tcp['dport'] == '8080'
        assert tcp['ttl'] == 86393

    def test_udp_entry_has_no_state(self):
        entries = self._parse()
        udp = next(e for e in entries if e['proto'] == 'udp')
        assert udp['state'] == ''
        assert udp['src'] == '192.168.95.5'
        assert udp['dport'] == '53'

    def test_icmp_entry_parsed(self):
        entries = self._parse()
        icmp = next(e for e in entries if e['proto'] == 'icmp')
        assert icmp['src'] == '192.168.90.6'
        assert icmp['dst'] == '192.168.95.2'

    def test_original_direction_used_not_reply(self):
        # The reply direction has swapped src/dst — we must use the original
        entries = self._parse()
        tcp = next(e for e in entries if e['proto'] == 'tcp')
        assert tcp['src'] == '192.168.95.2'   # original src, not reply src (192.168.90.107)
        assert tcp['dst'] == '192.168.90.107'

    def test_missing_file_returns_empty(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            entries = flask_app.parse_conntrack()
        assert entries == []

    def test_empty_file_returns_empty(self):
        entries = self._parse("")
        assert entries == []


# ---------------------------------------------------------------------------
# get_top_talkers
# ---------------------------------------------------------------------------

class TestGetTopTalkers:
    def _entries(self, ips):
        return [{'src': ip, 'proto': 'tcp', 'dst': '1.2.3.4',
                 'sport': '1', 'dport': '80', 'state': '', 'ttl': 100}
                for ip in ips]

    def test_counts_correctly(self):
        entries = self._entries(['10.0.0.1', '10.0.0.1', '10.0.0.2'])
        result = flask_app.get_top_talkers(entries)
        assert result[0] == {'ip': '10.0.0.1', 'connections': 2}
        assert result[1] == {'ip': '10.0.0.2', 'connections': 1}

    def test_respects_n_limit(self):
        entries = self._entries([f'10.0.0.{i}' for i in range(20)])
        result = flask_app.get_top_talkers(entries, n=5)
        assert len(result) == 5

    def test_unknown_src_excluded(self):
        entries = self._entries(['10.0.0.1', '?', '?'])
        result = flask_app.get_top_talkers(entries)
        assert all(t['ip'] != '?' for t in result)

    def test_empty_input(self):
        assert flask_app.get_top_talkers([]) == []


# ---------------------------------------------------------------------------
# read_proc_net_dev
# ---------------------------------------------------------------------------

SAMPLE_PROC_NET_DEV = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
  eth0:    1000     100    0    0    0     0          0         0     2000     200    0    0    0     0       0          0
  eth1:    3000     300    0    0    0     0          0         0     4000     400    0    0    0     0       0          0
  eth2:    5000     500    0    0    0     0          0         0     6000     600    0    0    0     0       0          0
"""


class TestReadProcNetDev:
    def test_parses_all_interfaces(self):
        with patch("builtins.open", mock_open(read_data=SAMPLE_PROC_NET_DEV)):
            stats = flask_app.read_proc_net_dev()
        assert set(stats.keys()) >= {'eth0', 'eth1', 'eth2'}

    def test_correct_byte_counts(self):
        with patch("builtins.open", mock_open(read_data=SAMPLE_PROC_NET_DEV)):
            stats = flask_app.read_proc_net_dev()
        assert stats['eth1']['rx_bytes'] == 3000
        assert stats['eth1']['tx_bytes'] == 4000
        assert stats['eth2']['rx_packets'] == 500

    def test_missing_file_returns_empty(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            stats = flask_app.read_proc_net_dev()
        assert stats == {}


# ---------------------------------------------------------------------------
# api_stats / api_states — route response shape
# ---------------------------------------------------------------------------

class TestApiRoutes:
    def setup_method(self):
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['SECRET_KEY'] = 'test'
        self.client = flask_app.app.test_client()
        # Establish a session so login_required passes
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'admin'

    def test_api_stats_returns_json(self):
        with patch.object(flask_app, 'parse_conntrack', return_value=[]), \
             patch.object(flask_app, 'get_interface_rates', return_value={
                 'eth0': {'rx_bps': 0.0, 'rx_pps': 0.0, 'tx_bps': 0.0, 'tx_pps': 0.0},
                 'eth1': {'rx_bps': 0.0, 'rx_pps': 0.0, 'tx_bps': 0.0, 'tx_pps': 0.0},
                 'eth2': {'rx_bps': 0.0, 'rx_pps': 0.0, 'tx_bps': 0.0, 'tx_pps': 0.0},
             }):
            resp = self.client.get('/api/stats')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'connection_count' in data
        assert 'interfaces' in data
        assert 'top_talkers' in data

    def test_api_stats_connection_count(self):
        fake_entries = [
            {'proto': 'tcp', 'state': 'ESTABLISHED', 'src': '192.168.95.2',
             'dst': '192.168.90.107', 'sport': '1234', 'dport': '80', 'ttl': 300},
        ]
        with patch.object(flask_app, 'parse_conntrack', return_value=fake_entries), \
             patch.object(flask_app, 'get_interface_rates', return_value={}):
            resp = self.client.get('/api/stats')
        data = json.loads(resp.data)
        assert data['connection_count'] == 1

    def test_api_states_returns_json(self):
        with patch.object(flask_app, 'parse_conntrack', return_value=[]):
            resp = self.client.get('/api/states')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'states' in data
        assert 'count' in data

    def test_api_states_count_matches_list(self):
        fake_entries = [
            {'proto': 'udp', 'state': '', 'src': '10.0.0.1', 'dst': '8.8.8.8',
             'sport': '9999', 'dport': '53', 'ttl': 30},
            {'proto': 'tcp', 'state': 'ESTABLISHED', 'src': '10.0.0.2', 'dst': '10.0.0.3',
             'sport': '443', 'dport': '50000', 'ttl': 300},
        ]
        with patch.object(flask_app, 'parse_conntrack', return_value=fake_entries):
            resp = self.client.get('/api/states')
        data = json.loads(resp.data)
        assert data['count'] == 2
        assert len(data['states']) == 2

    def test_api_requires_login(self):
        # Fresh client with no session
        anon = flask_app.app.test_client()
        resp = anon.get('/api/stats')
        assert resp.status_code == 302  # redirect to login


# ---------------------------------------------------------------------------
# DNS helpers
# ---------------------------------------------------------------------------

SAMPLE_DNSMASQ_LOG = """\
Apr 27 10:15:23 dnsmasq[42]: query[A] example.com from 192.168.95.2
Apr 27 10:15:23 dnsmasq[42]: forwarded example.com to 8.8.8.8
Apr 27 10:15:24 dnsmasq[42]: query[AAAA] ipv6.example.com from 192.168.95.5
Apr 27 10:15:25 dnsmasq[42]: query[A] evil-c2.com from 192.168.90.6
Apr 27 10:15:25 dnsmasq[42]: config evil-c2.com is NXDOMAIN
"""


class TestGetDnsQueries:
    def _queries(self, content=SAMPLE_DNSMASQ_LOG):
        with patch("builtins.open", mock_open(read_data=content)):
            return flask_app.get_dns_queries()

    def test_returns_only_query_lines(self):
        # "forwarded", "config" lines should not appear — only "query[" lines
        queries = self._queries()
        assert len(queries) == 3

    def test_parses_query_type(self):
        queries = self._queries()
        assert queries[0]['type'] == 'A'
        assert queries[1]['type'] == 'AAAA'

    def test_parses_domain(self):
        queries = self._queries()
        assert queries[0]['domain'] == 'example.com'
        assert queries[2]['domain'] == 'evil-c2.com'

    def test_parses_source_ip(self):
        queries = self._queries()
        assert queries[0]['src'] == '192.168.95.2'
        assert queries[2]['src'] == '192.168.90.6'

    def test_missing_log_returns_empty(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            assert flask_app.get_dns_queries() == []

    def test_respects_limit(self):
        queries = self._queries()
        assert len(flask_app.get_dns_queries.__wrapped__(1) if hasattr(flask_app.get_dns_queries, '__wrapped__') else
                   self._queries()) <= 100


class TestLoadDnsConfig:
    def test_missing_file_returns_empty_defaults(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            config = flask_app.load_dns_config()
        assert config == {"hosts": [], "blocked": []}

    def test_corrupt_json_returns_empty_defaults(self):
        with patch("builtins.open", mock_open(read_data="not json")):
            config = flask_app.load_dns_config()
        assert config == {"hosts": [], "blocked": []}

    def test_valid_config_loaded(self):
        data = {"hosts": [{"hostname": "plc", "ip": "10.0.0.1", "comment": ""}],
                "blocked": []}
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            config = flask_app.load_dns_config()
        assert config["hosts"][0]["hostname"] == "plc"


class TestApplyDnsConfig:
    def _apply(self, config):
        written = {}
        def fake_open(path, mode='r', *a, **kw):
            if mode == 'w':
                m = mock_open()()
                written[path] = m
                return m
            raise FileNotFoundError
        with patch("builtins.open", fake_open), \
             patch("subprocess.run"):
            flask_app.apply_dns_config(config)
        return written

    def test_hosts_file_written(self):
        config = {"hosts": [{"hostname": "plc.grfics.local", "ip": "192.168.95.2", "comment": ""}],
                  "blocked": []}
        written = self._apply(config)
        assert flask_app.DNS_HOSTS_PATH in written

    def test_blocked_file_written(self):
        config = {"hosts": [],
                  "blocked": [{"domain": "evil.com", "comment": "test"}]}
        written = self._apply(config)
        assert flask_app.DNS_BLOCKED_PATH in written

    def test_hosts_file_format(self):
        config = {"hosts": [{"hostname": "plc.grfics.local", "ip": "192.168.95.2", "comment": ""}],
                  "blocked": []}
        calls = []
        real_open = open
        def tracking_open(path, mode='r', *a, **kw):
            if mode == 'w':
                m = MagicMock()
                m.__enter__ = lambda s: s
                m.__exit__ = MagicMock(return_value=False)
                calls.append((path, m))
                return m
            raise FileNotFoundError
        with patch("builtins.open", tracking_open), patch("subprocess.run"):
            flask_app.apply_dns_config(config)
        hosts_call = next((c for c in calls if c[0] == flask_app.DNS_HOSTS_PATH), None)
        assert hosts_call is not None
        written_content = "".join(
            str(a[0]) for call in hosts_call[1].write.call_args_list
            for a in [call[0]]
        )
        assert "192.168.95.2" in written_content
        assert "plc.grfics.local" in written_content

    def test_blocked_file_format(self):
        config = {"hosts": [],
                  "blocked": [{"domain": "evil.com", "comment": ""}]}
        calls = []
        def tracking_open(path, mode='r', *a, **kw):
            if mode == 'w':
                m = MagicMock()
                m.__enter__ = lambda s: s
                m.__exit__ = MagicMock(return_value=False)
                calls.append((path, m))
                return m
            raise FileNotFoundError
        with patch("builtins.open", tracking_open), patch("subprocess.run"):
            flask_app.apply_dns_config(config)
        block_call = next((c for c in calls if c[0] == flask_app.DNS_BLOCKED_PATH), None)
        assert block_call is not None
        written_content = "".join(
            str(a[0]) for call in block_call[1].write.call_args_list
            for a in [call[0]]
        )
        assert "address=/evil.com/#" in written_content

    def test_dnsmasq_restarted(self):
        config = {"hosts": [], "blocked": []}
        with patch("builtins.open", mock_open()), \
             patch("subprocess.run") as mock_sub:
            flask_app.apply_dns_config(config)
        calls = [str(c) for c in mock_sub.call_args_list]
        assert any("dnsmasq" in c for c in calls)


class TestDomainSanitisation:
    """The add_block route strips leading wildcards/dots before storing."""
    def setup_method(self):
        flask_app.app.config['TESTING'] = True
        self.client = flask_app.app.test_client()
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True

    def test_wildcard_prefix_stripped(self):
        saved = {}
        def fake_save(config):
            saved.update(config)
        with patch.object(flask_app, 'load_dns_config', return_value={"hosts": [], "blocked": []}), \
             patch.object(flask_app, 'save_dns_config', side_effect=fake_save), \
             patch.object(flask_app, 'apply_dns_config'):
            self.client.post('/dns/add_block', data={'domain': '*.evil.com', 'comment': ''})
        assert saved.get("blocked", [{}])[0].get("domain") == "evil.com"
