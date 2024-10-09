from typing import Any
import os, random

scriptdir: str = os.path.dirname(__file__)
slow_test_coverage = int(os.getenv("SLOW_TEST_COVERAGE", "100"))


# ----------------------------------------------------------------- #
# return a random subset (slow_test_coverage %) of a large data set #
# ----------------------------------------------------------------- #
def random_subset(dataset: list[Any]) -> list[Any]:
    indices: set[int] = set()
    total = len(dataset)
    count = round(total * max(min(slow_test_coverage, 100), 0) / 100)
    while len(indices) < count:
        indices.add(random.randrange(total))
    return [dataset[i] for i in sorted(indices)]


# --------------------------------------------------------------------------- #
# build a dataset from a file and optionally thin it to slow_test_coverage %) #
# --------------------------------------------------------------------------- #
def dataset_from_file(filename: str, slow: bool = False) -> list[list[str]]:
    dataset: list[list[str]] = []
    with open(os.path.join(scriptdir, filename)) as f:
        for line in f.readlines():
            if not line or line.startswith("#"):
                continue
            dataset.append(list(line.strip().split("\t")))
    if slow:
        return random_subset(dataset)
    return dataset
