# nb1 tap preparation

- The user approved completing the formal tap and publishing the documentation site on 2026-11-17. The root agent controls repository visibility and remote publication after review.
- The product is nb1; the hardware is blink(1).
- A Formula is generated only from a verified published upstream release into
  an explicitly selected new local review directory. A verified production Formula
  and its release input/provenance may then be committed for publication. Keep
  materialized archives and temporary review outputs out of the repository;
  synthetic fixture data belongs only inside automated tests.
- Reuse the verified release's renderer/template. Do not add a second Formula
  implementation, synthetic install channel or automatic publishing/service step.
- Unit tests remain offline with mock HTTP. Native installation CI uses fresh
  hosted runners and the published source archive. Local acceptance uses only
  owned Homebrew prefixes/containers, never global Homebrew or existing services.
  No test requires physical USB. Public docs default to English, with Chinese
  alongside them.
