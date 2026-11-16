# Normative audit resolutions (spec v0.1.4, section 8)

These decisions make the contract explicit and supersede interpretations in
the test notes. MiB means 1024*1024 bytes; limits are inclusive. Described
objects are exact.

1. Compare ID lists element by element using ASCII; do not concatenate IDs.
2. Edge deduplication must not affect degrees, reachable or path; result
   independent of input order.
3. IDs are restricted ASCII; JSON key order/escapes are not criteria.
4. A path without a path is `None` in the API and JSON `null` in the CLI,
   never the string `"null"`.
5. The ID regex has inclusive limits: 32 characters valid, 33 invalid.
6. Failure to open/read FILE → exit 3; invalid JSON/schema after reading →
   exit 2. Other simultaneous errors are out of scope.
7. Complete sequence equality identifies the same observable result; internal
   route identity is out of scope.
8. `analyze` does no I/O, including network; the CLI only reads FILE and
   writes stdout/stderr. Do not consider the absence of failure proof of
   network blocking.
9. Inclusive limit of 1048576 bytes before parsing, counting whitespace;
   above → exit 2.
10. Duplicate nodes are invalid, not deduplicated: `ValueError` / CLI exit 2.
11. Argument IDs must be ASCII; Unicode only in paths, not IDs.
12. `edges` and each pair must be Python `list` in the API and JSON arrays in
    the CLI; tuples are invalid.
