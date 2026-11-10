import csv
import json
import tempfile
import unittest
from pathlib import Path
from core.data_logger import DataLogger

class CsvRoundtrip(unittest.TestCase):
    def test_raw_and_dictionary_rows_preserve_fields(self):
        inputs = ['pitch=1,roll=2', 'line one\nline two\r\n"quoted",中文', '', None,
                  {'pitch':1,'note':'a,"b"\n中文'}]
        with tempfile.TemporaryDirectory() as tmp:
            logger=DataLogger(tmp)
            logger.start_logging()
            for item in inputs: logger.log(item)
            logger.stop_logging()
            with open(logger.current_log_file, encoding='utf-8', newline='') as f:
                rows=list(csv.reader(f))
            self.assertEqual(len(rows), len(inputs))
            for item,row in zip(inputs,rows):
                self.assertEqual(len(row),3)
                self.assertRegex(row[0], r'^\d{4}-\d{2}-\d{2} ')
                if isinstance(item,dict):
                    self.assertEqual(row[1],'DICT')
                    self.assertEqual(json.loads(row[2]),item)
                else:
                    self.assertEqual(row[1],'RAW')
                    self.assertEqual(row[2],str(item))
    def test_simple_row_markers_still_match_existing_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger=DataLogger(tmp);logger.start_logging()
            logger.log('plain');logger.log({'source_mode':'SIMULATION / OFFLINE REPLAY'})
            logger.stop_logging()
            content=Path(logger.current_log_file).read_text(encoding='utf-8')
            self.assertIn(',RAW,',content);self.assertIn(',DICT,',content)
            self.assertIn('SIMULATION / OFFLINE REPLAY',content)

if __name__=='__main__': unittest.main()
