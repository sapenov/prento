# Verification log handling

These are actual execution logs, including failed diagnostic startup attempts and intentional mutation-test failures. Logs that contained the local project/workspace prefix have public copies with those prefixes replaced by `<PROJECT_ROOT>` / `<WORKSPACE>`. Paths of temporary diagnostic builds may be replaced by `<TEMP_BUILD>`. Content, exit outcomes and timing values are otherwise retained.

Original local copies are kept in ignored `qa-private/original-logs/` and are excluded from Git, Docker context and QA bundles. The previous QA ZIP also preserves the earlier originals locally. Redaction changes public-log checksums; new bundle hashes describe the supplied public copies.
