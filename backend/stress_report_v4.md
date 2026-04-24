# TORA Engine Stress Test Report
**Corpus**: 1200 queries · seed=42 · total run 1.8s · concurrency=20

**Mix**: {'2': 840, '1': 360} tracks, {'hinglish': 301, 'typos': 170, 'english': 729} styles, 20 personas

## Outcome summary

| Outcome | Count | % |
|---|---:|---:|
| ✓ track-2 primary plugin correct | 794 | 66.2% |
| ~ track-2 expected plugin as supporting | 32 | 2.7% |
| ✗ track-2 matched but wrong plugin | 6 | 0.5% |
| ✗ track-2 got zero matches | 8 | 0.7% |
| ✓ track-1 correctly skipped enrichment | 338 | 28.2% |
| ✗ track-1 leaked to a plugin | 22 | 1.8% |
| ✗ engine raised | 0 | 0.0% |

## Headline metrics

- **Track-2 recall** (right plugin found): `98.3%` (826/840 hits, 8 misses, 6 wrong plugin)
- **Track-1 precision** (no false enrichment): `93.9%` (338/360 clean, 22 false positives)

## Per-category recall (track-2)

| Category | Queries | Hit | Hit-supporting | Wrong | Miss | Recall |
|---|---:|---:|---:|---:|---:|---:|
| appliances | 70 | 70 | 0 | 0 | 0 | 100.0% |
| education | 70 | 61 | 9 | 0 | 0 | 100.0% |
| electronics | 70 | 70 | 0 | 0 | 0 | 100.0% |
| furniture | 70 | 56 | 14 | 0 | 0 | 100.0% |
| gold | 70 | 65 | 5 | 0 | 0 | 100.0% |
| healthcare | 70 | 65 | 0 | 1 | 4 | 92.9% |
| investments | 70 | 70 | 0 | 0 | 0 | 100.0% |
| lifestyle | 70 | 70 | 0 | 0 | 0 | 100.0% |
| mobility | 70 | 66 | 0 | 0 | 4 | 94.3% |
| real_estate | 70 | 70 | 0 | 0 | 0 | 100.0% |
| travel | 70 | 65 | 0 | 5 | 0 | 92.9% |
| wedding | 70 | 66 | 4 | 0 | 0 | 100.0% |

## Per-style accuracy

| Style | Queries | Track-2 recall | Track-1 precision |
|---|---:|---:|---:|
| english | 729 | 99.0% (482) | 91.1% (247) |
| hinglish | 301 | 96.1% (228) | 100.0% (73) |
| typos | 170 | 100.0% (130) | 100.0% (40) |

## Thinking-mode gating

- Accuracy vs expected: `97.5%` (1170/1200)

## Latency distribution (ms)

- mean:  20.47
- p50:   22.94
- p95:   40.44
- p99:   47.68
- max:   60.85
- queries above 800ms budget: 0 (0.00%)

## Plugin match volume (all queries combined)

| Plugin | Times matched |
|---|---:|
| real_estate | 105 |
| investments | 100 |
| travel | 99 |
| appliances | 85 |
| wedding | 82 |
| gold | 80 |
| lifestyle | 78 |
| furniture | 76 |
| education | 70 |
| mobility | 70 |
| electronics | 70 |
| healthcare | 65 |

## Top problematic queries (actionable)

### false_pos in `trap_tv` (n=15)

- `I have too many tvs in my house for the guests` → matched: real_estate(house,primary), appliances(tv,supporting)
- `I have too many tvs in my house for the guests` → matched: real_estate(house,primary), appliances(tv,supporting)
- `I have too many tvs in my house for the guests` → matched: real_estate(house,primary), appliances(tv,supporting)
- `I have too many tvs in my house for the guests` → matched: real_estate(house,primary), appliances(tv,supporting)
- `I have too many tvs in my house for the guests` → matched: real_estate(house,primary), appliances(tv,supporting)
- _(+10 more)_

### false_pos in `savings_query` (n=7)

- `how much can i save if i cut dining out` → matched: lifestyle(dining,primary)
- `how much can i save if i cut dining out` → matched: lifestyle(dining,primary)
- `how much can i save if i cut dining out` → matched: lifestyle(dining,primary)
- `how much can i save if i cut dining out` → matched: lifestyle(dining,primary)
- `how much can i save if i cut dining out` → matched: lifestyle(dining,primary)
- _(+2 more)_

### wrong_plugin in `travel` (n=5)

- `honeymoon ke liye budget plan karo` → matched: wedding(honeymoon,primary)
- `honeymoon ke liye budget plan karo` → matched: wedding(honeymoon,primary)
- `honeymoon ke liye budget plan karo` → matched: wedding(honeymoon,primary)
- `honeymoon ke liye budget plan karo` → matched: wedding(honeymoon,primary)
- `honeymoon ke liye budget plan karo` → matched: wedding(honeymoon,primary)

### miss_track2 in `healthcare` (n=4)

- `how much cover do i need at age 35` → matched: —
- `how much cover do i need at age 35` → matched: —
- `how much cover do i need at age 35` → matched: —
- `how much cover do i need at age 35` → matched: —

### miss_track2 in `mobility` (n=4)

- `mere surplus me EMI afford kar sakta hu kya` → matched: —
- `mere surplus me EMI afford kar sakta hu kya` → matched: —
- `mere surplus me EMI afford kar sakta hu kya` → matched: —
- `mere surplus me EMI afford kar sakta hu kya` → matched: —

### wrong_plugin in `healthcare` (n=1)

- `normal vs c-section delivery charges` → matched: lifestyle(delivery,primary)

