# FB-GAZE-01 dataset interchange format v1

**Important:** The current implementation consumes *combined gaze*, normalized
onto an explicit rectilinear visual field, not raw eye orientation data. This is
an experimental interchange layer and cannot preserve all original optical
information. New stereo and 3D-ray schema will be introduced separately.

A dataset CSV must have exactly these header fields:

```csv
trace_id,subject_id,timestamp_ns,gaze_x,gaze_y,valid
session-a,subject-01,0,0.50,0.50,1
session-a,subject-01,11111111,0.52,0.50,1
session-a,subject-01,22222222,,,0
session-a,subject-01,33333333,0.55,0.51,1
```

- `trace_id`: unique stable identifier per continuous recording/session;
  timestamps strictly increasing *within* each trace.
- `subject_id`: stable pseudonymous participant identifier across sessions.
  Avoid real names and personally identifying details.
- `timestamp_ns`: signed integer offset from monotonic recording time origin;
  must be nonnegative, in nanoseconds, not seconds or frame indices.
- `gaze_x`, `gaze_y`: finite normalized [0,1] UV; X grows right, Y grows down.
  Coordinates require documented transformation. Empty for invalid observations.
- `valid`: 1/0 or true/false. Invalid gaze is not interpolated in ground truth.

The metadata JSON must supply exactly these *string* fields:

```json
{
  "dataset_id": "dataset-version-id",
  "source_kind": "recorded",
  "source_url": "https://example.org/publication-or-repository",
  "license": "confirmed-right-to-use-license-or-terms",
  "consent_status": "approved-secondary-use-or-public-release-terms",
  "coordinate_system": "normalized_uv_top_left",
  "timebase": "relative_monotonic_ns",
  "sampling_description": "original Hz / resampling details",
  "eye_channel": "combined_gaze",
  "device_and_firmware": "device and firmware or unknown",
  "calibration": "manufacturer procedure / validation error or unknown",
  "processing": "all filtering, interpolation, coordinate and binocular choices",
  "data_loss": "fraction and missingness mechanism or unknown",
  "measurement_uncertainty": "precision and accuracy if known, else unknown",
  "signal_latency": "measured latency, if known; unknown otherwise"
}
```

For recorded data, license and consent must be *explicitly confirmed*;
`unknown` values in those two fields are rejected. Declared metadata is
**not** independent verification of participant authenticity or legal rights.

The runner accepts no more than one subject per trace ID. It does not
randomize/merge subjects and no population inference is currently performed.

## Run

```bash
python -m foveabench.phase1 validate-dataset \
  --dataset path/to/gaze.csv --dataset-manifest path/to/metadata.json
python -m foveabench.phase1 run \
  --dataset path/to/gaze.csv --dataset-manifest path/to/metadata.json \
  --output results/my-recorded-run
```

The manifest embeds content SHA256 fingerprints and provenance snapshots, while
privacy-sensitive raw recording data are NOT copied into the output bundle.

## Eye tracker reporting

See Dunn et al., *Minimal reporting guideline for research involving eye
tracking*, https://pmc.ncbi.nlm.nih.gov/articles/PMC11225961/ . Their minimum
items include hardware/firmware, tracking technology, eye channels, calibration,
measurement uncertainty, processing, data loss and signal latency.

See Khronos OpenXR gaze sample semantics:
https://registry.khronos.org/OpenXR/specs/1.1/man/html/XrEyeGazeSampleTimeEXT.html
The sample time can differ from requested pose time, and zero means unknown.

Until a calibrated adapter exists, do **not** interpret normalized-UV offsets
as verified anatomical angles on an HMD display. The current pinhole 90-degree
FOV is only a specified virtual camera.
