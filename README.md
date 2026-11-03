# Take-home task: Smart meter billing

## The setting

We are WattWunder, an electricity provider. Our customers have smart meters and a time-of-use tariff: cheaper electricity at night.

One customer, say a bakery, wants to understand this month's bill: how much it is and why, without calling our support.

You will build the part of our system that computes the bill from the raw meter readings, and the screen the customer sees. Backend and frontend together, one repo.

## What to build

1. **Bill calculation.** Read the meter data and the tariff, compute the customer's bill for the month, expose it through an API (shape and protocol are yours).
2. **The customer's screen.** What goes on it is your decision. UI text in German, written for the customer, not for an energy engineer.

Backend in Python or TypeScript/JavaScript, frontend in TypeScript or JavaScript, any framework. Storage is your call; we'll ask why in the follow-up.

Skip authentication and authorisation: assume the customer is already logged in.

Optional, only if you have time left: an endpoint for meters to report new readings.

## The data

| File | What it is |
| --- | --- |
| `readings.csv` | One month of 15-minute meter readings from the customer's meter: `timestamp, energy_wh` |
| `tariff.json` | The customer's tariff: day price 06:00–22:00, night price otherwise, both in ct/kWh, plus a fixed monthly fee in €. |

## Brand

Use our logo `logo.svg`, the font [Figtree](https://fonts.google.com/specimen/Figtree) and our colours: `#0F2A3F` navy (primary), `#F5A623` amber (accent), `#F7F5F0` off-white (background).

## Rules

- Bill each 15-minute interval at the price valid for it.
- If this task description doesn't answer a question, make your own decision and write it down.
- Tests are expected.

## What you hand in

- The code, with a `README.md` that gets it running in under five minutes.
- `NOTES.md`, one page at most. This file matters as much as the code. Include:
  - the total your code computes for the month
  - the decisions you made on questions this task description doesn't answer
  - what you put on the customer's screen and what you left off
  - which AI tools and models you used, and how you checked their output
  - what you'd build next

## What we look at

1. **Is the bill right.** This is the minimum.
2. **Judgment.** The decisions in `NOTES.md`, how you checked your AI's output, and how well you explain both.
3. **Does the customer get it.** Can the customer read the screen in 30 seconds and believe the number?
4. **Code we'd want to live with.** Clear structure, tests that matter, no cleverness for its own sake.
5. **The call.** Can you explain your solution and change it together with us?

We don't score framework choice, pixel polish, or how much you built. A smaller thing done well beats a bigger thing done roughly.

## Practicalities

- **Time:** plan for 2–3 hours. Stop there, even if it's unfinished.
- **AI:** use whatever you like. We care about judgment, not typing. Your choice of tools doesn't count for or against you.
- **Setup:** unzip this into a new private GitHub repository of your own. When you're done, add `fex80enop`, `amorelli-enopai` and `mykyta-ishchenko-enopai` as collaborators and send a short email to felix.alcala@enopai.com and raz.reichhold@enopai.com.
- **Deadline:** within one week. If life gets in the way, say so; that's fine.
- **Your code:** we use it only to evaluate your application.
- **Next step:** a 60-minute call. You walk us through your solution, then we extend it together, AI allowed.
