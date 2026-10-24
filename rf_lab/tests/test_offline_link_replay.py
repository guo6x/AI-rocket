"""Synthetic replay has fixed expected behavior without any radio."""
import unittest
from rf_lab.offline_link_replay import replay

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
        self.assertEqual(counts['SESSION_CHANGED'],1)
    def test_known_number_of_synthetic_events(self):
        self.assertEqual(replay()['event_count'],21)
    def test_forward_gaps_not_called_confirmed_packet_losses(self):
        r=replay()
        self.assertGreaterEqual(r['unobserved_sequence_total'],3)
        self.assertIn('not measured packet-loss',r['warning'])
    def test_replay_determinism(self):
        self.assertEqual(replay(),replay())

if __name__ == '__main__':
    unittest.main()
