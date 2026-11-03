# Notes

## The total

October 2026 comes to **2.295,99 €**. That is the gross amount and includes 366,59 € VAT (net 1.929,40 €).

| Line | Quantity | Price | Amount |
| --- | --- | --- | --- |
| Day (06:00 to 22:00) | 4.562,796 kWh | 31,847 ct | 1.453,11 € |
| Night | 4.279,988 kWh | 19,392 ct | 829,98 € |
| Monthly fee | 1 | 12,90 € | 12,90 € |

`make crosscheck` recomputes the month in pandas, with no app imports, floats and one rounding at the end: 1.453,1136 + 829,9753 + 12,90 gives the same 2.295,99 €. A golden API test pins the three lines.

## Decisions the task left open

- Time zone: Europe/Berlin. Timestamps are stored in UTC; each interval is priced by its local start (06:00 day, 22:00 night).
- 25 Oct, 02:00 to 02:45 twice: the DST fall-back, not duplicates. 100 intervals that day, all at night price, explained in a notice.
- 08 Oct 10:15, two values (2419 and 3200 Wh): the later one wins as a corrected resend. The old value is kept and the screen says "korrigiert".
- 13 Oct 14:30 missing: interpolated from its neighbours (2288 Wh, 0,73 €) and marked "geschätzt".
- Missing data in general: I assume readings are sent by the meter automatically, not by the customer, so a gap is our problem and the customer should not pay for consumption we never measured. Following that, only gaps up to one hour between two real readings are estimated; anything longer is not billed and the screen says how many hours are missing. An empty month is a fee-only bill. The running month is billed up to the latest reading ("laufender Monat").
- VAT: the task doesn't mention it. I assume the tariff prices are gross, so the total is the plain sum and the 19 % VAT inside it is shown separately. If they are net (common for B2B), the total is 19 % higher; `PRICES_INCLUDE_VAT=false` switches to that. I would confirm this with product.
- Rounding: `Decimal` throughout, each line rounded half-up to cents, total = sum of lines. The chart's per-day euros are rounded per day, so they can differ from the lines by a few cents.
- Monthly fee: full 12,90 €, not prorated.
- Storage: SQLite with SQLAlchemy and Alembic: no install, and ingest needs somewhere to write. The CSV is imported through the same ingest service as the API.
- Ingest: batch upsert per meter, 422 for invalid readings, at most 2,980 readings (a full month with the DST hour) and 1 MB per request.

## The screen

The bill comes first: the total with VAT, then the three lines that add up to it. Then one sentence on what the night price saved ("48 % Ihres Stroms lief nachts … rund 533 € weniger"), a daily day/night chart (kWh or €, tap a day for detail), and one plain sentence per notice. One breakpoint at 600 px for phones. The month switcher serves the `make demo` data.

Left off: an hour-of-day chart and a comparison with last month.

## AI tools and how I checked them

I used Claude Code with Claude Opus and spent most of the effort on planning before any code. I wrote the open questions down as decision tickets and settled them one at a time: what the data hides, how to price an interval, VAT, rounding, storage, and what the customer needs on screen. Those decisions became a spec, and the spec became small build tickets.

The edge cases came from reading the raw CSV, not from guessing: the repeated hour on 25 Oct, the two values on 8 Oct and the missing interval on 13 Oct. Each got a test before its code (the "Trap test (red)" commits fail on purpose), and the questions they raised, such as what to bill when data is missing, turned into the decisions above.

For the screen I started from what a bakery owner needs in 30 seconds: the total, lines that add up to it, and one plain sentence for anything unusual in the data. I prototyped three layouts with the real numbers and picked the one that shows the bill first.

To check the AI's output, an independent pandas script recomputes the total, and after each ticket two fresh review agents compared the diff with the coding standards and the spec. They caught real bugs, for example a month with a single reading being billed as a full month.

## Known gaps

No auth on ingest beyond the meter's public ID, and no range check on timestamps. The stale-types test covers `openapi.json`, not the generated TypeScript. One meter per customer. Chart tap tested by emulation only.

## Next

Device tokens and rate limiting for meters, tariff prices with validity dates, and a month-over-month comparison as the real "why".
