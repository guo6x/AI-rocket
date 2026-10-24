"""Synthetic replay has fixed expected behavior without any radio."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from rf_lab.offline_link_replay import main, replay

class ReplayTests(unittest.TestCase):
    def test_synthetic_read_only(self):
        r=replay()
        self.assertTrue(r['synthetic_only'])
        self.assertEqual(r['radio_transmissions'],0)
        self.assertEqual(r['flight_commands'],0)
    def test_fault_types_distinguished(self):
        counts=replay()['counts']
        self.assertEqual(counts['DUPLICATE'],1)
        self.assertEqual(counts['STALE_OR_OUT_OF_ORDER'],1)
        self.assertEqual(counts['REJECT_crc_mismatch'],1)
        self.assertEqual(counts['SESSION_CHANGED'],2)
    def test_known_number_of_synthetic_events(self):
        self.assertEqual(replay()['event_count'],24)
    def test_forward_gaps_not_called_confirmed_packet_losses(self):
        r=replay()
        self.assertEqual(r['unobserved_sequence_total'],4)
        self.assertIn('not measured packet-loss',r['warning'])
    def test_replay_determinism(self):
        self.assertEqual(replay(),replay())
    def test_replay_sequence_wrap_uses_codec_and_window(self):
        events=replay()['events']
        wrapped=[event for event in events if event['label'].startswith('wrap_')]
        self.assertEqual([event['label'] for event in wrapped], [
            'wrap_session', 'wrap_before_zero', 'wrap_to_zero'
        ])
        self.assertEqual([event['status'] for event in wrapped], [
            'SESSION_CHANGED', 'ACCEPT', 'ACCEPT'
        ])
        self.assertEqual([event['sequence'] for event in wrapped], [65534,65535,0])
        self.assertEqual(wrapped[-1]['unobserved_sequence_count'],0)
    def test_faults_cover_loss_duplicate_reorder_corruption_and_session(self):
        counts=replay()['counts']
        self.assertEqual(counts, {
            'ACCEPT': 19,
            'DUPLICATE': 1,
            'REJECT_crc_mismatch': 1,
            'SESSION_CHANGED': 2,
            'STALE_OR_OUT_OF_ORDER': 1,
        })
        self.assertEqual(replay()['fault_schedule']['synthetic_drops'], [
            {'session_id':17,'sequence':103},
            {'session_id':17,'sequence':104},
        ])
    def test_evidence_binds_input_sources_path_and_reproduction_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'rf evidence.json'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--write-evidence',str(output)]),0)
            record=json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(record['artifact_path'],output.as_posix())
        self.assertEqual(record['reproduction_command'],
            "py -3 -m rf_lab.offline_link_replay --write-evidence '"+output.as_posix()+"'")
        canonical=json.dumps({
            'fault_schedule':record['fault_schedule'],
            'input_trace':record['input_trace'],
        },sort_keys=True,separators=(',',':')).encode('ascii')
        self.assertEqual(record['input_trace_sha256'],hashlib.sha256(canonical).hexdigest())
        self.assertRegex(record['source_git_sha'],r'^[0-9a-f]{40}$')
        self.assertEqual(record['source_worktree_clean'],not record['source_worktree_changes'])
        self.assertEqual(set(record['source_sha256']), {
            'engineering/rf-offline-contract.yaml',
            'docs/R3_RF_OFFLINE_PROTOCOL.md',
            'rf_lab/telemetry_frame.py',
            'rf_lab/offline_link_replay.py',
            'rf_lab/tests/test_telemetry_frame.py',
            'rf_lab/tests/test_offline_link_replay.py',
            'scripts/check.py',
        })
        self.assertTrue(all(re.fullmatch(r'[0-9a-f]{64}',value)
                            for value in record['source_sha256'].values()))
        self.assertEqual(record['evidence_ceiling'],'TESTED_SOFTWARE')
        self.assertEqual(record['seed'],'not_applicable_fixed_trace')
        self.assertTrue(record['synthetic_only'])
        self.assertFalse(record['physical_hardware'])
        self.assertEqual(record['radio_transmissions'],0)
        self.assertEqual(record['flight_commands'],0)
        self.assertFalse(record['crc_is_authentication'])

if __name__ == '__main__':
    unittest.main()
