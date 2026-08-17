from __future__ import annotations

import timeit

from proofsmith.git_adapter import parse_numstat
from proofsmith.impact import plan_for

DIFF = "\n".join(f"{index % 7 + 1}\t{index % 3}\tsrc/module_{index}.py" for index in range(1000))


def run() -> None:
    files = parse_numstat(DIFF)
    elapsed = timeit.timeit(lambda: plan_for(files), number=1000)
    print(
        f"files={len(files)} iterations=1000 total_seconds={elapsed:.6f} per_plan_ms={elapsed:.3f}"
    )


if __name__ == "__main__":
    run()
