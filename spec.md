Ring Dataset Generation – Inner Diameter (Pixel) Supervision
1. Goal

Create a dataset of RGB images from a Blender scene (ring_shader_pos1.blend) containing a single ring object named ring.

The dataset must simulate a human photographing a ring placed on a table, from different distances and angles, while guaranteeing that:

The ring is always fully visible in the image

The ring is not too far away (never tiny in frame)

Camera pose varies realistically

The ring’s inner diameter is varied in a controlled, parametric way

The inner diameter in pixels is recorded as the primary training label

The dataset is intended for ML / CV use, so reproducibility, consistency, and metadata quality are critical.

The current training target is inner diameter in pixels, with the assumption that a future reference will enable conversion to true physical size.

2. Non-goals (explicitly out of scope)

Free-form or destructive mesh editing

Non-parametric geometry changes

Material, lighting, or background randomization

Segmentation, depth, or masks (RGB only, unless explicitly extended later)

Interactive / UI-based Blender operations (headless only)

Pixel-to-mm conversion (future phase)

3. Target Object Definition

The target object is named ring

It is assumed to be:

A mesh object, OR

An empty whose children contain the renderable mesh(es)

The ring must expose a parametric control for its inner diameter via one of:

Geometry Nodes parameter (preferred)

Shape key

Custom property with driver

Direct vertex-level mesh editing is not allowed.

If:

the object ring is not found, OR

no parametric inner diameter control exists

→ the program must fail loudly with a clear error.

4. Scene Assumptions

The ring is placed on a table-like surface

World +Z is "up"

The ring rests approximately flat

No explicit table object is required

The table plane is inferred as:

table_plane_z = min_z of ring world-space bounding box

5. Geometry Randomization (Inner Diameter)
5.1 Authoritative principle

True size variation must come from geometry, not camera pose alone.

Camera variation is used to avoid trivial correlations, but inner diameter diversity is driven by geometry randomization.

5.2 Geometry behavior per sample

For each dataset sample:

A target inner diameter parameter is sampled from a configured range

The ring geometry is updated via its parametric control

Camera pose is sampled and validated

The image is rendered

The inner diameter in pixels is measured from the rendered result

The image and labels are stored

Geometry updates must be:

deterministic

reversible or overwrite-safe

isolated to the inner diameter parameter

not affect materials, textures, or shading

6. Camera Model ("Human photographing a ring on a table")
6.1 Degrees of freedom

Camera pose is randomized:

Position

Orientation (look-at)

No roll unless explicitly allowed (default: no roll).

Camera intrinsics (focal length, sensor size) must be fixed and logged.

6.2 Camera sampling space

Camera poses are sampled from a hemisphere above the table, centered on the ring.

Angular constraints

Yaw (azimuth):
Full range: 0°–360°

Pitch / elevation:
Default: 25°–75°
Never fully top-down unless explicitly configured

Distance constraints (relative, not absolute)

Distances are defined relative to ring size:

R = ring bounding sphere radius
min distance = 10 × R
max distance = 35 × R


This ensures:

Close-ups are possible

Ring never appears “far away”

Scene scale does not matter

7. Camera Orientation

The camera must look at the ring center

A small look-at jitter is allowed to simulate imperfect human framing:

Max jitter ≤ 10% of R

Camera "up" must remain aligned with world up

No unnatural roll

8. Visibility & Framing Constraints (Hard Requirements)

Every generated image must satisfy all of the following:

8.1 Full visibility

All vertices of the ring’s world-space bounding box, when projected into image space:

Must lie fully inside the image

With a safety margin of at least 7% from each image edge

8.2 Not too far away

The projected ring bounding box must occupy at least:

20–35% of image width or height (configurable)

This prevents “technically visible but tiny” cases.

8.3 Correction before rejection

If a candidate pose violates constraints:

Attempt auto-correction:

Increase distance slightly

Reduce pitch if near extremes

Re-check visibility

If still invalid after bounded attempts → reject and resample

9. Inner Diameter Measurement (Pixel Label)
9.1 Definition (authoritative)

Inner diameter is the diameter of the inner hole of the ring

Measured in image-space pixels

Measurement axis:

Major axis of the projected inner-hole ellipse

One scalar label per image:

inner_diameter_px

9.2 Measurement method

The pixel diameter must be derived from image-space evidence, not only from 3D projection math.

Recommended approach:

Render an auxiliary binary measurement pass isolating the ring silhouette

Detect the inner hole region in 2D

Fit an ellipse to the hole contour

Use the major axis length (pixels) as the label

This ensures:

Labels match what the model “sees”

Perspective effects are correctly encoded

10. Sampling, Rejection, and Distribution Control

Each dataset sample may attempt up to N attempts (default: 30–60)

Rejection reasons must be tracked:

Cropped

Too small

Below table plane

Invalid projection

Invalid inner diameter measurement

The system must never enter an infinite loop

The pipeline must support explicit control of the pixel-diameter distribution, including:

min / max pixel diameter

optional binning for balanced datasets

Samples outside the desired pixel range must be rejected and resampled.

11. Dataset Output
11.1 File structure
dataset/
├── images/
│   ├── 000000.png
│   ├── 000001.png
│   └── ...
├── annotations.jsonl
├── labels.csv        (optional convenience)
└── run_config.json

11.2 Image output

RGB images only

Deterministic naming

11.3 Metadata (annotations.jsonl)

Each record must include:

Image path

inner_diameter_px ← primary training label

Camera intrinsics

Camera extrinsics

Sampled camera parameters:

yaw

pitch

distance

Geometry parameters:

inner diameter parameter value used

Visibility metrics

Seed

11.4 Reproducibility

Each run must record:

Seed

Blender version

Config values

Ring object name (ring)

12. Execution Model

Must run in headless Blender:

blender -b ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- [args]


No reliance on Blender UI state
No modal operators

13. Acceptance Criteria (Definition of Done)

The implementation is considered correct when:

100% of images contain the ring fully visible with margin

No image shows the ring:

clipped

partially outside frame

extremely small

Inner diameter pixel labels:

exist for every image

fall within configured bounds

Camera viewpoints clearly vary in:

angle

distance

Two runs with the same seed produce identical outputs

Rejection rate is non-zero but bounded

Output metadata is sufficient for downstream metric-to-physical calibration

14. Extension Points (future, not now)

Pixel-to-mm conversion via reference object

Segmentation masks

Depth maps

Lighting randomization

Multiple rings

COCO / YOLO export

15. Authority Clause

If any implementation decision conflicts with this document,
this document takes precedence.