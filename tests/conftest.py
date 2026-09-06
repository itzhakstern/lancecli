from __future__ import annotations

import lance
import numpy as np
import pyarrow as pa
import pytest
from typer.testing import CliRunner

N_ROWS = 100
APPEND_ROWS = 10


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def dataset_uri(tmp_path) -> str:
    uri = str(tmp_path / "events.lance")
    ids = list(range(N_ROWS))
    names = [f"user_{i}" for i in ids]
    ages = [20 + (i % 50) for i in ids]
    embedding = np.arange(N_ROWS * 4, dtype=np.float32)
    table = pa.table(
        {
            "id": pa.array(ids, type=pa.int64()),
            "name": pa.array(names),
            "age": pa.array(ages, type=pa.int64()),
            "embedding": pa.FixedSizeListArray.from_arrays(
                pa.array(embedding, type=pa.float32()),
                4,
            ),
        }
    )
    lance.write_dataset(table, uri)
    extra = table.slice(0, APPEND_ROWS)
    lance.write_dataset(extra, uri, mode="append")
    ds = lance.dataset(uri)
    ds.create_scalar_index("age", "BTREE")
    return uri
