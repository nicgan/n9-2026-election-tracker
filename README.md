# PRN16 Negeri Sembilan · Election Intelligence Dashboard

A live-tracking dashboard and forecasting model for the 16th Negeri Sembilan state election (**PRN16 · polling day 1 August 2026**). Built as a static site with a Monte Carlo forecasting layer, twice-daily automated news + sentiment sweeps, and a post-election accuracy review.

**Live site (retired):** https://n9prn.pplx.app

---

## What it did

- Forecast government-formation probability and per-seat winners for all **36 DUN** across Negeri Sembilan's 7 districts (Jelebu, Jempol, Seremban, Kuala Pilah, Rasah, Rembau, Port Dickson, Tampin).
- Ran a **Monte Carlo simulation** (10,000 draws) over seat-level `probs` distributions calibrated from 2023 results, 2018 baseline swing, candidate quality, incumbency, ethnic-composition, and campaign priors.
- Refreshed twice daily (**07:30 MYT** morning brief + **19:00 MYT** evening campaign update) from **1 Jul → 2 Aug 2026** via scheduled tasks that:
  1. Read the current state (`data/model_output.json`, `data/intel.json`).
  2. Swept mainstream news (Bernama, FMT, Malaysiakini, CNA, The Edge, Malay Mail, Sinar Harian, Utusan, Berita Harian, Harakah, The Vibes, pilihanraya.my) for candidate movements, official statements, ceramah coverage, polls, and misinformation.
  3. Sampled social sentiment on X, TikTok, Facebook, and Threads for PH / BN / PN / Bersatu.
  4. Only re-ran the Monte Carlo on **genuine material events** (new poll, party leader change, incumbent scandal, coordinated race/religion campaign, royal-dispute update).
  5. Updated `intel.json` (executive block, momentum, sentiment, coordinated_flags, narratives_up/down, candidates, risks, polls, watchlist, changelog).
  6. Re-deployed and re-published the live site.
  7. Sent an in-app + Telegram notification with the day's headline movement.
- Delivered a **post-election accuracy review** on 2 Aug 2026 comparing the final forecast to official EC results.

---

## Final scorecard (2 Aug 2026)

**Official EC result:** BN 18 · PN 7 · PH 11 · **BN+PN combined 25 = two-thirds majority.** Turnout 72.64% (646,084 voters).

| Metric | Model | Actual | Verdict |
| --- | --- | --- | --- |
| Government formation | **BN+PN 73%** | BN+PN two-thirds | ✅ Direction correct |
| Per-seat accuracy | 30 of 36 correct | — | **83.3%** |
| Within-coalition confusion | 0 seats | — | Perfect |
| BN+PN mean seat count | 18.5 | 25 | −6.5 underestimate |
| PH mean seat count | 17.5 | 11 | +6.5 overestimate |

### Biggest hits
- Called BN+PN government from Day 1 through 3 weeks of mainstream hedging (Ilham Centre and Ong Kian Ming both revised down toward the model's call in the final week).
- Called **Aminuddin Harun** (caretaker Menteri Besar) losing Linggi.
- Flagged UMNO+PAS informal cooperation and the Hadi PAS-vote-BN directive as the biggest single risk repeatedly across April→July.

### Biggest misses — all 6 seats were PH called that flipped
| Seat | Model call | Actual winner | Margin |
| --- | --- | --- | --- |
| **N01 Chennah** | PH (Anthony Loke) | BN — Siow Kong Choon (MCA) | 688 |
| **N13 Sikamat** | PH | PN — Razali Abu Samah | 4,413 |
| **N14 Ampangan** | PH | PN — Mohamad Rafie | 3,969 |
| **N18 Pilah** | PH | BN — S Leza | 730 |
| **N25 Paroi** | PH | PN — Kamarol Ridzuan | 16,959 |
| **N36 Repah** | PH | BN — Koh Kim Swee | 444 |

**Root cause:** UMNO+PAS informal cooperation delivered ~6pp stronger Malay-vote consolidation than the model's priors captured. This is the coordinated race/religion effect that `narratives_up` flagged repeatedly but which priors treated as marginal.

### Casualties
- **Anthony Loke** (DAP secretary-general, federal Transport Minister) lost Chennah after 3 terms.
- **Aminuddin Harun** (caretaker Menteri Besar) lost Linggi.
- **Amanah wiped out**: 0 seats from 7 contested.
- **Bersatu shut out**: 0 seats from 24 own-logo contests.

---

## Repository structure

```
ns-tracker/
├── README.md                  # this file
├── index.html                 # dashboard shell (15 sections)
├── build_model.py             # Monte Carlo forecasting engine
├── css/
│   └── style.css              # design tokens, layout, dark-mode
├── js/
│   └── app.js                 # renderer — reads data/*.json, hydrates DOM
├── data/
│   ├── model_output.json      # per-seat probs, coalition seat stats, final scored actuals
│   └── intel.json             # executive block, momentum, sentiment, narratives, polls, changelog
└── img/                       # any generated visual assets
```

### `build_model.py` — forecasting engine

- Encodes all 36 DUN with fields: `code`, `name`, `parl`, `ethnic` (mixed / mixed_chinese / malay_dominant / malay_super), `y2023_winner`, `y2023_maj_pct`, `contest` (2-way / 3-way / 4-way), `candidates` (with `party`, `name`, `incumbent`, `star`).
- Applies **prior adjustments** for:
  - 2023 majority (safe / competitive / marginal)
  - Ethnic composition swing sensitivity
  - Incumbency bonus (~4pp)
  - Star candidate bonus (~2pp, e.g. Loke, Aminuddin, Tok Mat)
  - Contest type (Bersatu-PN split penalty in 3-way Malay contests)
  - Campaign-window priors set from the twice-daily briefings
- Runs 10,000 Monte Carlo draws → produces `probs` per seat, `leader`, `leader_prob`, `classification` (Safe / Likely / Lean / Toss-up).
- Aggregates coalition seat statistics (`mean`, `median`, `p10`, `p90`, `min`, `max`, `p_majority`).
- Outputs government-formation probabilities for PH, BN+PN, and Hung/Other.

### `data/intel.json` — narrative layer

Structured content that hydrates the dashboard:

- **`meta`** — `generated_at` (ISO 8601 MYT), `confidence_notes`
- **`executive`** — `probability_pct`, `headline`, `subhead`, `current_call`, `surprise_scenario`, `watchlist`, `predicted_winner_short`
- **`momentum`** — per-party rating (Positive-Strong / Negative / Winner / Loser) + drivers
- **`sentiment`** — per-platform (X / FB / TikTok / Threads) per-party sentiment with notes
- **`coordinated_flags`** — timestamped notes on influence operations, misinformation, coordinated campaigns
- **`narratives_up`** / **`narratives_down`** — rising and fading storylines with impact tags
- **`candidates`** — watched candidates with race, threat level
- **`risks`** — risk register with probability × impact
- **`polls`** — external projections (Ilham, INVOKE, Ong Kian Ming, Merdeka Center) + EC turnout snapshots
- **`markets`** — betting markets where available
- **`changelog`** — top 30 prepended entries with dated summaries

### `js/app.js` — renderer

- Zero build step. Vanilla JS, ES2020.
- Fetches `data/intel.json` and `data/model_output.json` at load.
- Renders 15 dashboard sections: hero, executive brief, forecast, watchlist, per-seat table with sortable columns, momentum, sentiment, coordinated flags, narratives, candidates, risks, polls, markets, changelog.
- Includes hardened fallbacks (e.g. `|| 'BN+PN'`) for missing fields.

---

## Methodology

### Analytical standards
- **Verified reporting > party statements > online rumours.**
- **Flag coordinated influence campaigns** — logged 72 flags across the run.
- **Weight fresher information.** Priors updated on the twice-daily briefing cadence.
- **State uncertainty explicitly.** Every executive block includes a `surprise_scenario`.
- **Never fabricate a poll or a quote.** All external projections cited to source.

### Model priors (final week)
- BN+PN informal pact given 65% base probability of government formation
- Bersatu-PN internal split penalty: −3pp per 3-way Malay contest where Bersatu ran its own logo
- Star candidate bonus: Loke +2pp, Aminuddin +2pp, Tok Mat +3pp, Wee Ka Siong campaign effect
- Chinese/urban turnout risk to PH: identified 28 Jul evening; flagged 3× before polling day
- Royal-dispute overhang: monitored throughout; ultimately not a decisive factor

### What the model got right → what it missed
The model correctly identified the **direction** but under-weighted the **magnitude** of Malay-vote consolidation. Future iterations should:
1. Model informal party cooperation as a **coalition-level effect** rather than seat-level adjustment when both parties publicly endorse vote transfer.
2. Weight Chinese/urban turnout under-performance more heavily when it is flagged in the final 72h.
3. Give more prior weight to same-day analyst revisions (Ong Kian Ming's Aug 1 downgrade to BN-PN 17 was the closest external call to the actual 25 outcome).

---

## Timeline of updates

- **19 Jul 2026** — dashboard v1 (HTML shell, CSS, JS renderer, initial intel + model data)
- **21 Jul** — header prob consistency fix, nav wrap
- **28 Jul** — priors edited to BN+PN 73% (from ~65%)
- **29-30 Jul** — CoA DKU stay, Sanusi Lord's Day sermon, Hadi PAS-vote-BN directive, Anwar Klana temple apology, Utusan ballot-test framing
- **31 Jul morning** — Anwar Munajat Perdana (Linggi + Kuala Pilah), pondok-schools post-poll pledge
- **31 Jul evening** — Ilham Centre projection (BN-PN 22 / PH 9 / TCTC 5), Ong Kian Ming reaffirms BN-PN 23-25, IDERC "too close to call"
- **1 Aug polling day morning** — silence-period fake graphics (AFP flagged), MACC 4 cash-distribution probes, MetMalaysia clear-morning forecast
- **1 Aug polling day evening** — polls closed 6pm, turnout 65.38% at 4pm (+3.49pp vs 2023), Ong revised BN-PN down to 17, The Edge 5pm tally showed BN leading in 9 Malay-majority seats
- **2 Aug** — post-election accuracy review, dashboard retired, both crons deleted

---

## Technology

- **Frontend:** vanilla HTML/CSS/JS (no framework), static site deployed to `*.pplx.app` sandbox
- **Model:** Python 3, NumPy Monte Carlo (`build_model.py`)
- **Automation:** Perplexity Computer twice-daily scheduled tasks
- **Notifications:** in-app + Telegram (via Pipedream bot `@negeri9bot`)
- **Sources:** mainstream Malaysian media, EC official announcements, party statements, X / TikTok / FB / Threads sentiment sweeps

---

## Related projects

Documented in the user's knowledge wiki:

- `projects/negeri-sembilan-2026-election-intelligence` — this dashboard
- `projects/negeri-sembilan-2026-sentiment-tracker` — companion Johor-method N9 sentiment tracker
- `projects/johor-2026-sentiment-tracker` — the completed sibling project this one's method was derived from

---

## License

Personal project. Not licensed for redistribution. Contents include third-party news snippets and party statements cited to their original publishers.

---

_Retired 2 Aug 2026 after PRN16 official results announced by EC Chairman Datuk Seri Ramlan Harun at 11.57pm on 1 Aug 2026._
