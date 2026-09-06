"""Create a tiny local Lance dataset for trying lancecli."""

from __future__ import annotations

from pathlib import Path

import lance
import numpy as np
import pyarrow as pa

N_ROWS = 50


def main() -> None:
    root = Path(__file__).resolve().parent
    uri = str(root / "events.lance")
    ids = list(range(N_ROWS))
    table = pa.table(
        {
            "id": pa.array(ids, type=pa.int64()),
            "name": pa.array([f"user_{i}" for i in ids]),
            "age": pa.array([20 + (i % 40) for i in ids], type=pa.int64()),
            "city": pa.array(["TLV", "NYC", "BER", "LON"][i % 4] for i in ids),
            "embedding": pa.FixedSizeListArray.from_arrays(
                pa.array(np.arange(N_ROWS * 4, dtype=np.float32), type=pa.float32()),
                4,
            ),
        }
    )
    lance.write_dataset(table, uri, mode="overwrite")
    print(uri)


if __name__ == "__main__":
    main()
