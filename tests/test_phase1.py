"""FB-GAZE-01 numerical integrity and runner integration tests."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

from foveabench.phase1 import (
    Sample, Observation, angular_error, generate_rows, load_config, load_csv,
    observations, package_run, predict, synthetic_traces, validate_manifest,
    verify_samples,
)

PROFILE = Path(__file__).resolve().parents[1] / 'benchmark_spec/profiles/fb-gaze-01.json'

class Phase1ContractTests(unittest.TestCase):
    def test_synthetic_reproducible(self):
        a=synthetic_traces(7,90,60,2)
        self.assertEqual(a,synthetic_traces(7,90,60,2))
        self.assertNotEqual(a,synthetic_traces(8,90,60,2))

    def test_angle_and_validity(self):
        self.assertLess(angular_error(.5,.5,.5,.5,90,90),1e-5)
        self.assertGreater(angular_error(.5,.5,.8,.5,90,90),10)
        with self.assertRaises(ValueError):
            verify_samples([Sample('a','s',0,.5,.5,True),Sample('a','s',0,.5,.5,True)])

    def test_out_of_order_delivery_uses_newest_sample(self):
        arrivals=[Observation(20_000_000,25_000_000,.3,.3),
                  Observation(0,30_000_000,.1,.1)]
        self.assertEqual(predict(arrivals,"hold",35_000_000,80,160)[:2],(.3,.3))

    def test_causal_delivery_no_lookahead(self):
        future=Observation(20_000_000,80_000_000,.9,.9)
        past=Observation(0,0,.2,.2)
        self.assertEqual(predict([past], 'hold', 50_000_000,80,160)[:2],(.2,.2))
        # The engine must NEVER append future, even if sample timestamps earlier.
        inputs=[past] if future.delivered_ns>50_000_000 else [past,future]
        self.assertEqual(predict(inputs,'hold',50_000_000,80,160)[:2],(.2,.2))

    def test_latency_changes_delivery(self):
        samples=[Sample('x','s',i*10_000_000,.3+i*.02,.4,True) for i in range(8)]
        c={'dropout_probability':0,'latency_ms':40,'jitter_sigma_ms':0,'noise_sigma_deg':0}
        obs=observations(samples,seed=7,condition=c,hfov=90,vfov=90)
        self.assertTrue(all(o.delivered_ns-o.sample_ns==40_000_000 for o in obs))
        self.assertEqual(sum(x.delivered_ns<=20_000_000 for x in obs),0)

    def test_reject_unlicensed_recorded_dataset(self):
        obj={k:'unknown' for k in ('dataset_id','source_kind','source_url','license',
                'consent_status','coordinate_system','timebase','sampling_description',
                'eye_channel','device_and_firmware','calibration','processing','data_loss',
                'measurement_uncertainty','signal_latency')}
        obj.update(source_kind='recorded', coordinate_system='normalized_uv_top_left',
                   timebase='relative_monotonic_ns',eye_channel='combined_gaze')
        with self.assertRaises(ValueError):
            validate_manifest(obj,synthetic=False)

    def test_reject_out_of_range_and_duplicate_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input.csv'
            p.write_text('trace_id,subject_id,timestamp_ns,gaze_x,gaze_y,valid\n'
                         'a,s,0,0.5,0.5,1\na,s,1,1.5,0.5,1\na,s,2,0.5,0.5,1\n')
            with self.assertRaises(ValueError):load_csv(p)

    def test_full_automated_experiment(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            config=json.loads(PROFILE.read_text())
            config['synthetic_frames']=30
            config['synthetic_sessions_per_kind']=1
            config['conditions']=[config['conditions'][0],config['conditions'][2]]
            config_path=root/'config.json'
            config_path.write_text(json.dumps(config))
            output=root/'run'
            package_run(config_path=config_path,output=output,seed=5,
                        data_path=None,metadata_path=None)
            m=json.loads((output/'manifest.json').read_text())
            self.assertEqual(m['frames'],30*3*2*2)
            self.assertEqual(m['checks']['causal_observation_delivery'],'PASS')
            self.assertTrue((output/'summary.csv').exists())
            self.assertTrue((output/'report.md').exists())
            with (output/'summary.csv').open() as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),4)
            self.assertIn("meets_quality_gate",rows[0])
            with self.assertRaises(FileExistsError):
                package_run(config_path=config_path,output=output,seed=5,
                            data_path=None,metadata_path=None)

if __name__ == '__main__': unittest.main()
