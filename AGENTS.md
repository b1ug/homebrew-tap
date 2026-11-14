# nb1 tap preparation

- Keep this repository private until the user explicitly changes that scope.
- The product is nb1; the hardware is blink(1).
- A Formula is generated only from a verified published upstream release into
  an explicitly selected new local review directory. Keep materialized test
  archives and generated review outputs out of the repository; synthetic fixture
  data belongs only inside automated tests.
- Reuse the verified release's renderer/template. Do not add a second Formula
  implementation, synthetic install channel or automatic publishing/service step.
- Tests are offline and use mock HTTP. They do not access USB, daily daemons,
  global Homebrew or user configuration. Public docs default to English, with
  Chinese alongside them.
