"""Visual renderer contracts: PNG correctness, timestamped synthetic traces, provenance."""
import csv
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from foveabench.showcase import PNG_SIGNATURE, demo_trace, png_chunk, ppm_to_png, _read_metrics


class VisualShowcaseTests(unittest.TestCase):
    def test_png_encoder_valid_crc_and_rgb(self):
        data = ppm_to_png(b"P6\n2 1\n255\n" + bytes((255, 0, 0, 0, 255, 0)))
        self.assertTrue(data.startswith(PNG_SIGNATURE))
        offset=len(PNG_SIGNATURE)
        payload=[]
        kinds=[]
        while offset<len(data):
            length=struct.unpack(">I",data[offset:offset+4])[0]
            kind=data[offset+4:offset+8]
            content=data[offset+8:offset+8+length]
            crc=struct.unpack(">I",data[offset+8+length:offset+12+length])[0]
            self.assertEqual(crc,zlib.crc32(kind+content)&0xffffffff)
            kinds.append(kind)
            if kind==b"IDAT":payload.append(content)
            offset+=12+length
        self.assertEqual(kinds,[b"IHDR",b"IDAT",b"IEND"])
        self.assertEqual(zlib.decompress(b"".join(payload)),bytes((0,255,0,0,0,255,0)))

    def test_png_encoder_rejects_invalid(self):
        for bad in (b"P3\n2 1\n255\n000", b"P6\n2 1\n255\nshort"):
            with self.assertRaises(ValueError):ppm_to_png(bad)

    def test_gaze_timebase_and_hold_is_causal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"trace.csv"
            demo_trace(p,48,90,"hybrid",60)
            rows=list(csv.DictReader(p.open()))
            self.assertEqual(len(rows),48)
            self.assertTrue(all(int(rows[i]["timestamp_ns"])>int(rows[i-1]["timestamp_ns"])
                                for i in range(1,len(rows))))
            self.assertEqual(float(rows[0]["truth_x"]),float(rows[0]["used_x"]))
            for i,r in enumerate(rows):
                lag=max(0,i-6)
                self.assertAlmostEqual(float(r["used_x"]),float(rows[lag]["truth_x"]))
            with self.assertRaises(FileExistsError):demo_trace(p,48,90,"hybrid",60)

    def test_reject_inconsistent_native_policy_frames(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with (p/"frames.csv").open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["scene","policy","frame_index","timestamp_ns",
                    "truth_x","truth_y","used_x","used_y","weighted_mse","foveal_mse",
                    "sample_fraction_proxy","device_dispatch_ms"])
                w.writeheader()
                w.writerow(dict(scene="chirp",policy="tracked",frame_index=0,timestamp_ns=0,
                                truth_x=.5,truth_y=.5,used_x=.5,used_y=.5,weighted_mse=1,
                                foveal_mse=1,sample_fraction_proxy=.1,device_dispatch_ms=""))
            with self.assertRaises(ValueError):_read_metrics(p)

if __name__ == "__main__":unittest.main()
