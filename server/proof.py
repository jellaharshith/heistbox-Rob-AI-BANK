"""Z3 check of the RIGHT vault's integer projection (and nothing more).

For n rows with amounts a_i >= 0 that matched the entitlement, remaining r >= 0, and
prefix sums P_i = a_1 + ... + a_i, the SQL computes  allowed_i = max(0, min(a_i, r - (P_i - a_i))).
We prove, for every n up to N_MAX, that for ALL integer inputs:
  (1) 0 <= allowed_i <= a_i
  (2) sum(allowed_i) <= r                      -- never pays more than the remaining entitlement
  (3) sum(allowed_i) == min(r, sum(a_i))       -- never withholds money the entitlement covers
This is a property of the arithmetic formula. It is not a proof about prompts, the LLM, or that the
SQL text equals the formula (tests/attack_suite cross-checks the live SQL against a Python oracle).
"""
from __future__ import annotations

import time

N_MAX = 12


def prove(n_max: int = N_MAX) -> dict:
    try:
        import z3
    except ImportError:
        return {"status": "unavailable", "detail": "z3-solver not installed"}
    t0 = time.perf_counter()
    for n in range(1, n_max + 1):
        a = [z3.Int(f"a{i}") for i in range(n)]
        r = z3.Int("r")
        s = z3.Solver()
        s.add(r >= 0, *[x >= 0 for x in a])
        allowed, prefix = [], 0
        for x in a:
            prefix = prefix + x
            room = r - (prefix - x)
            allowed.append(z3.If(z3.If(x < room, x, room) > 0, z3.If(x < room, x, room), 0))
        total_a, total = z3.Sum(a), z3.Sum(allowed)
        props = z3.And(
            *[z3.And(al >= 0, al <= x) for al, x in zip(allowed, a)],
            total <= r,
            total == z3.If(r < total_a, r, total_a),
        )
        s.add(z3.Not(props))
        res = s.check()
        if res != z3.unsat:
            return {"status": "counterexample", "n": n, "model": str(s.model()) if res == z3.sat else str(res),
                    "solve_ms": round((time.perf_counter() - t0) * 1000, 1)}
    return {"status": "proved", "n_checked": f"1..{n_max}",
            "properties": ["0 <= allowed_i <= a_i", "sum(allowed) <= remaining", "sum(allowed) == min(remaining, sum(a))"],
            "scope": "integer projection formula only; not a claim about prompt safety",
            "solve_ms": round((time.perf_counter() - t0) * 1000, 1)}
