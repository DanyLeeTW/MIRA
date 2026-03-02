import json
import pathlib
from collections.abc import Sized
from typing import Sequence

import pandas as pd


class ConsortTracker:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reset()
        return cls._instance

    def node(self, key: str, n: int | None = None) -> None:
        """Register/overwrite a box.  n=None means 'fill later'."""
        if key not in self._counts:
            self._order.append(key)
        if n is not None:
            self._counts[key] = n

    def edge(self, src: str, dst: str) -> None:
        """Declare a directed connection between boxes."""
        self._edges.add((src, dst))

    def count(self, key: str, n_or_iterable: int | Sized) -> None:
        """
        Convenience helper:
          • If you give me an int, I use it as-is.
          • Otherwise I store len(obj).
        """
        n = n_or_iterable if isinstance(n_or_iterable, int) else len(n_or_iterable)
        self.node(key, n)

    def to_graphviz(
        self,
        filename: str = "consort",
        fmt: str = "pdf",
        curved: bool = False,
    ):
        from graphviz import Digraph

        g = Digraph("CONSORT", format=fmt)
        g.graph_attr.update(
            rankdir="TB",
            splines="true",
            pack="true",
            packmode="clust",
        )
        g.attr(
            "node",
            shape="box",
            style="filled, rounded",
            color="black",
            fillcolor="#f0f0f0",
            fontname="Helvetica",
            fontsize="10",
        )
        g.attr(
            "edge",
            fontsize="10",
            fontname="Helvetica-Bold",
        )

        for k in self._order:
            label_txt = f"{k}\n(n={self._counts.get(k, '?')})"
            if k.lower().startswith("validated cohort"):
                g.node(k, label_txt, fillcolor="#c8f7c5")
            elif k.lower().startswith("excluded"):
                g.node(k, label_txt, fillcolor="#f8cccc")
            else:
                g.node(k, label_txt)

        for a, b in self._edges:
            g.edge(a, b)

        # enforce left→right order on bottom row
        bottom_row = [
            "Excluded – invalid lab events",
            "Excluded – invalid radiology",
            "Validated cohort",
        ]
        with g.subgraph(name="rank_bottom") as s:
            s.attr(rank="same")
            for n in bottom_row:
                if n in self._counts:  # node must exist
                    s.node(n)
            s.edge(bottom_row[0], bottom_row[1], style="invis")
            s.edge(bottom_row[1], bottom_row[2], style="invis")

        return g.render(filename, cleanup=True)

    def count_unique(
        self,
        label: str,
        df: pd.DataFrame | None = None,
        cols: Sequence[str] | None = None,
        n: int | None = None,
    ):
        """
        • If you pass a DataFrame + column(s) → counts unique rows of those cols.
        • If you pass an int directly (n=…)  → records that number verbatim.
        """
        if n is None:
            if df is None or cols is None:
                raise ValueError("Need either n=… or df+cols.")
            n = df.drop_duplicates(list(cols)).shape[0]
        self.node(label, n)

    def reset(self) -> None:
        self._counts: dict[str, int] = {}
        self._edges: set[tuple[str, str]] = set()
        self._order: list[str] = []

    def save(self, path: str):
        """Write counts, edges, order to JSON so you can resume later."""

        data = {
            "counts": self._counts,
            "edges": list(self._edges),
            "order": self._order,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str):
        """Load a previously saved JSON snapshot and overwrite in-memory state."""

        if not pathlib.Path(path).exists():
            raise FileNotFoundError(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # rebuild internal structures
        self._counts = {k: int(v) for k, v in data["counts"].items()}
        self._edges = {tuple(e) for e in data["edges"]}
        self._order = list(data["order"])


tracker = ConsortTracker()
