# SSL Dataset — details

Videos of individual Saudi Sign Language signs from the [Saudi Sign Language Library](https://sshi.sa/)
(Saudi Society for Hearing Impairment). One video = one sign, labelled with the website's own Arabic
title (primary) and its English translation. Collected 2026-11-06.

## Summary

| | |
|---|---|
| Sign entries found on the site | 8,822 (36 categories; ID-gap probe of 3,839 IDs found no unlisted entries) |
| Downloaded successfully | 8,816 |
| Failed downloads | 6 (file missing on server — see below) |
| Redundant duplicates removed | 53 (42 groups) |
| **Videos in dataset** | **8,763** (2.7 GB, 7.96 h) |
| Unique Arabic labels (classes) | 8,191 |
| Videos with Arabic label | 8,763 |
| Videos with English translation | 8,761 |
| Labels flagged `needs_manual_review` | 208 |
| Format | MP4 (H.264), mostly 1920×1080 @ 25 fps (418 at 1280×720; some 30/60 fps), originals not re-encoded |

## Layout

```
dataset/
├── videos/<NN_category>/ssl_<word_id>.mp4   # Git LFS
└── metadata/
    ├── dataset.csv / dataset.json   # one record per video
    ├── labels.csv                   # one row per class (label_id ↔ label_ar / label_en)
    ├── categories.csv               # category id/names, counts on site vs in dataset
    ├── duplicates_report.json       # duplicate groups and which entries were merged
    ├── download_log.json            # every download attempt, URL, bytes, sha256, errors
    ├── qc_report.json               # results of scripts/validate_dataset.py
    └── raw/                         # unmodified API responses (words, categories, posters,
                                     #   sentence packs, YouTube media list)
```

`video_id` is `ssl_` + the site's 5-digit word ID, so every record links back to
`https://sshi.sa/category/<category_id>/<word_id>`.

## Metadata fields (`dataset.csv`)

| Field | Meaning |
|---|---|
| `video_id` | Unique ID (`ssl_00039`) |
| `filename` | Path relative to `dataset/videos/` |
| `label_ar` | Arabic sign name exactly as published (whitespace/tatweel normalised) |
| `label_en` | English translation as published (empty if the site gave none) |
| `category` / `category_ar` / `category_en` / `category_id` | Site category |
| `label_id` | Integer class index (see `labels.csv`) |
| `source_url` | Original video file URL |
| `source_page` | Website page for the sign |
| `duration` | Seconds (from the file) |
| `file_format` | `mp4` |
| `verification_status` | `source_label` or `needs_manual_review` |
| `review_reasons` | Why a record was flagged (`;`-separated) |
| `aliases_ar` | Other labels the same video is published under (merged duplicates) |
| `description_ar`, `synonym` | Site description / synonym text |
| `width`, `height`, `fps`, `num_frames`, `file_size`, `sha256` | Technical info |
| `site_word_id`, `original_filename` | Site identifiers |

## Labelling and verification

Labels are **not** invented or machine-translated; they are the site's `wordAr` / `wordEn` fields.
`verification_status = source_label` means the label was taken verbatim and passed automatic checks.
It does **not** mean a signer has reviewed it. `needs_manual_review` (208 videos) is set when:

| Reason | Count | Meaning |
|---|---|---|
| `source_filename_differs` | 180 | The original upload was named after a different word (e.g. label «دلفين», file «سمك القرش.mp4») — the clip may be mislinked |
| `duplicate_conflict` | 28 | The identical video is published under different Arabic labels |
| `label_en_not_english` | 1 | The "English" field contained Arabic (English left empty) |
| `placeholder_label` | 1 | Label looks like a filename/variant tag (`شفوق_3`) |

For training you may want to filter to `verification_status == "source_label"`.

## Duplicates

The site uses one video file per entry, but 42 groups of entries share byte-identical videos.
For each group the lowest word ID is kept; the other entries' labels are kept in `aliases_ar`
and listed in `duplicates_report.json`. Re-encoded copies of the same clip (different bytes)
are not detected.

## Not collected

* **6 entries whose video file is missing on the server** (the URL returns an empty HTML page):
  word IDs 737 «مسجد النمرة», 6163 «مواطنة», 10274 «البحر الميت», 10276 «صنعاء العاصمة»,
  10277 «طرابلس العاصمة», 10290 «مسقط العاصمة».
* **2 YouTube episodes** in the Education/Entertainment sections — embedded from YouTube,
  catalogued in `metadata/raw/youtube_media.json` but not downloaded (YouTube terms of service).
* **Sentences** (`/sentences`) reuse the dictionary clips in sequence; no extra video files. The
  sentence packs (useful for continuous-signing work) are saved in `metadata/raw/sentences.json`.
* **English letters** (`/letters-en`) is a static chart image, not videos.

## Categories

The suggested `greetings/numbers/family/education/other` folders were replaced by the site's own
36 categories, so no category labels had to be guessed.

| ID | Folder | Arabic | English | On site | In dataset |
|---|---|---|---|---|---|
| 1 | `01_signal_alphabet_letters` | الحروف الأبجدية الإشارية | Signal alphabet letters | 38 | 38 |
| 2 | `02_signal_numbers` | الأرقام الإشارية | Signal numbers | 43 | 42 |
| 3 | `03_directions_and_positions` | اتجاهات ومواضع | Directions and Positions | 16 | 16 |
| 4 | `04_management_economics_and_accounting` | ادارة واقتصاد ومحاسبة | Management, Economics And Accounting | 67 | 67 |
| 5 | `05_adjectives_and_states` | صفات وحالات | Adjectives And States | 229 | 229 |
| 6 | `06_shapes_and_colors` | أشكال والوان | Shapes And Colors | 28 | 28 |
| 7 | `07_education_and_training` | تعليم وتدريب | Education And Training | 170 | 168 |
| 8 | `08_environment_and_nature` | بيئة وطبيعة | Environment And Nature | 133 | 131 |
| 9 | `09_space` | الفضاء | Space | 12 | 12 |
| 10 | `10_home` | المنزل | HOME | 279 | 279 |
| 11 | `11_correctional_systems_and_prisons` | الأنظمة الإصلاحية والسجون | Correctional Systems and Prisons | 52 | 52 |
| 12 | `12_descriptive_ordinal_numbers` | الاعداد الترتيبية الوصفية | Descriptive Ordinal Numbers | 30 | 30 |
| 13 | `13_health_and_illness` | الصحة والمرض | Health And Illness | 153 | 152 |
| 14 | `14_social_relations` | باب العلاقات الاجتماعية | Social relations | 207 | 207 |
| 15 | `15_family_and_society` | الاسرة والمجتمع | Family and Society | 79 | 78 |
| 16 | `16_the_opposite` | باب الضداد | The Opposite | 41 | 41 |
| 18 | `18_traffic_and_transportation` | مرور ونقل | Traffic And Transportation | 125 | 124 |
| 19 | `19_jobs_and_careers` | وظائف ومهن | Jobs And Careers | 42 | 42 |
| 20 | `20_measures_and_times` | مقايسس وازمنة | Measures And Times | 61 | 61 |
| 21 | `21_national` | وطني | National | 366 | 366 |
| 22 | `22_variety_video` | مصطلحات متنوعة | Variety Video | 8 | 8 |
| 23 | `23_religion_and_worship` | باب الدين | Religion and worship | 1529 | 1521 |
| 24 | `24_social_education` | التربية الاجتماعية | Social Education | 471 | 468 |
| 25 | `25_coputer` | الحاسوب | Coputer | 229 | 229 |
| 26 | `26_scince` | العلوم | Scince | 961 | 952 |
| 30 | `30_sports_and_arts` | الرياضة و الفنون | Sports And Arts | 170 | 167 |
| 31 | `31_cities_and_states` | دول العالم ومدنها | Cities and States | 138 | 134 |
| 33 | `33_flay` | طيران ناس | flay | 9 | 9 |
| 35 | `35_arabic_languge` | اللغة العربية | Arabic Languge | 1421 | 1410 |
| 36 | `36_art` | الفنية | Art | 319 | 316 |
| 37 | `37_math` | رياضيات | Math | 347 | 343 |
| 38 | `38_family_education` | التربية الاسرية | Family Education | 796 | 791 |
| 39 | `39_common_words` | الكلمات الشائعة | Common Words | 162 | 161 |
| 52 | `52_academy` | أكاديمية | Academy | 60 | 60 |
| 53 | `53_health_terminology` | مصطلحات في الصحة | Health Terminology | 29 | 29 |
| 54 | `54_category` | مفردات وتراكيب متعلقة بالجنة | — | 2 | 2 |

Category English names (including typos such as "Scince", "Coputer") are kept as published;
category 54 has no English name on the site.

## Licence

Videos and labels © Saudi Society for Hearing Impairment (sshi.sa). Collected from the public site
(robots.txt allows crawling) for non-commercial research. This repository does not relicense them;
cite the source and contact SSHI for other uses.
