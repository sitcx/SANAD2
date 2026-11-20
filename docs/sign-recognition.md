# Sign recognition

**Status:** the code is ready and tested with synthetic data, but the gallery is still empty, so
real signs are not recognised yet. Building it needs the dataset videos (Git LFS) and a Python 3.12
environment (mediapipe has no wheel for newer Python).

## How it works

1. The browser runs MediaPipe Hands on the camera and sends **keypoints only** (no video leaves the device).
2. `recognize_sign` compares each sign with the gallery using **DTW** (dynamic time warping), which
   tolerates signing faster or slower. No model training.
3. Before comparing, each frame is centred and scaled, so hand position and distance from the camera
   do not matter — only the hand shape and movement.
4. The top words per sign go to `compose_sentence`, which writes 3 Arabic options.

Code: `src/agent/inference/sign_model.py`.

## Keypoint format

One sign = a list of frames; one frame = **42 points** `[x, y]` in 0–1 image coordinates:

| Points | Hand |
|---|---|
| 0–20 | left hand (MediaPipe Hands landmarks) |
| 21–41 | right hand |

A missing hand is 21 points of `[0, 0]`. Frames with no hands at all are dropped. The browser must send
the same layout that `build_gallery.py` saves.

## Building the gallery

1. Choose the interview vocabulary (`config.yaml` → `signs.vocabulary_size`, 40 words) and write one
   Arabic label per line, exactly as in `src/data/dataset/metadata/dataset.csv` (column `label_ar`),
   into `src/data/sign_gallery/vocabulary.txt`.
2. Download the videos you need:

   ```bash
   git lfs pull --include "src/data/dataset/videos/19_jobs_and_careers/*"
   ```

3. In a Python 3.12 environment:

   ```bash
   pip install mediapipe opencv-python numpy pyyaml python-dotenv
   python -m src.agent.inference.build_gallery --words-file src/data/sign_gallery/vocabulary.txt
   ```

The script writes `labels.json` and `<label_id>__<n>.npy` files (up to 3 examples per word,
`--max-per-word`) and logs every video as `[OK]`, `[SKIP]` (not downloaded / no hands) or a warning for
words not in the dataset.

## Gallery files

```
src/data/sign_gallery/
├── vocabulary.txt        the words to include (you write this)
├── labels.json           {"<label_id>": "<label_ar>"}
└── <label_id>__0.npy     keypoints, shape (frames, 42, 2)
```
