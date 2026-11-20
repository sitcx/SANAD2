# Data

| Path | Content |
|---|---|
| `jobs.json` | Jobs the Job Agent searches (English version of the 3 demo jobs in the web UI) |
| `sign_gallery/` | Keypoints of the ~40 interview words (small `.npy` files) |
| `sample_cvs/` | Sample CVs for the demo |
| `dataset/` | Saudi Sign Language dataset: 8,763 sign videos + metadata (see `dataset/README.md`) |

## Dataset videos (Git LFS)

The videos are stored with Git LFS (about 2.7 GB in total). After checkout they are small
pointer files until downloaded. Download only what you need, for example one category:

```bash
git lfs pull --include "src/data/dataset/videos/19_jobs_and_careers/*"
```

or everything (2.7 GB):

```bash
git lfs pull
```

`dataset/metadata/dataset.csv` lists every video with its Arabic / English label and category.
