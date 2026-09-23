# Working on main

More than one coding agent pushes to `main`, and the live site deploys from it. These rules keep
the checks green and the site in step with them.

1. Run the full check before every push, in this order, and push only when all of it passes:

   ```
   python scripts/validate.py
   cd site && npx astro check && npm run build && npm test && cd ..
   python -m unittest discover -s tests
   ```

   Build before the Python tests: some of them read `site/dist` and skip without it.

2. If a test fails because the site changed on purpose, update the test in the same commit and
   say in the commit message what it checks now. Keep what it was protecting (a quotation, an
   audit trail, an accessibility property) checked somewhere, even if the page no longer shows it.

3. Deploy only with `gh workflow run pages.yml --ref main`. The deploy waits for `checks` on the
   same commit and refuses to run if they failed, so a red push stops at the gate.

4. Push `main` only. Never `git push --all` or `--mirror`.

5. Nothing about the site's owner goes in the tracked tree, including a name from git config.
   Synthetic people and addresses use the reserved `.test` domain and are allowlisted in
   `tests/test_no_owner_name.py` file by file.

`CONTRIBUTING.md` covers sourcing and quotations; `docs/WRITING-A-TECHNIQUE-PAGE.md` covers pages.
