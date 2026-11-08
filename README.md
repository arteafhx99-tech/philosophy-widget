# Daily Philosophy Widget

## Setup
1. Create a PUBLIC GitHub repository (e.g. `philosophy-widget`). Upload the files in this directory, preserving `.github/workflows/update.yml`.
2. In repository Settings → Actions → General, allow GitHub Actions to run. Set Workflow permissions to **Read and write permissions** if necessary. The workflow also declares `contents: write`.
3. Optional AI commentary: create an OpenAI API key in platform.openai.com, enable API billing, and add it as repository Settings → Secrets and variables → Actions → New repository secret named `OPENAI_API_KEY`. Never paste this key into Scriptable or commit it. Without a key, the system rotates the curated notes automatically and costs no OpenAI API usage.
4. Run Actions → Update philosophy widget → Run workflow once. Check `daily-philosophy.json` updates in the repository.
5. Open `Scriptable.js`, replace `YOUR_GITHUB_USERNAME` and `YOUR_REPO` in the URL, then paste the entire script into the existing Scriptable `Daily Philosophy` script.
6. Keep your existing medium Scriptable widget bound to that script. Run script once to test.

## Notes
- UTC 20:00 is Beijing 04:00 the next day; UTC 10:00 is Beijing 18:00 the same day.
- GitHub Actions scheduled workflows may be delayed; iOS widget refresh is not exact.
- The included curated library has only TWO verified quotes; add more carefully verified entries to `quotes.json` to avoid repeats. Do not set `verified:true` until the original and source are checked.
- The OpenAI API is independent from ChatGPT Tasks; they will not necessarily publish the same quote.
- A PUBLIC repo exposes quote data, not API secrets. Do not store private information in it.
- API model availability and billing are account-dependent. Adjust `OPENAI_MODEL` in the workflow if needed.
