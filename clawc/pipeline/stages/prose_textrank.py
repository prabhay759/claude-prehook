from __future__ import annotations

import re
from abc import ABC, abstractmethod

_MIN_SENTENCES = 8
_KEEP_RATIO = 0.4
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


class ProseTextrank(Stage):
    name = "prose_textrank"

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        if len(text) < 500:
            return None

        sentences = _SENT_SPLIT.split(text.strip())
        if len(sentences) < _MIN_SENTENCES:
            return None

        try:
            import networkx as nx
        except ImportError:
            return None

        words = [frozenset(re.findall(r"\w+", s.lower())) for s in sentences]
        G: nx.Graph = nx.Graph()
        G.add_nodes_from(range(len(sentences)))

        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                union = words[i] | words[j]
                if union:
                    sim = len(words[i] & words[j]) / len(union)
                    if sim > 0:
                        G.add_edge(i, j, weight=sim)

        if G.number_of_edges() == 0:
            return None

        scores = nx.pagerank(G, weight="weight")
        keep_n = max(1, int(len(sentences) * _KEEP_RATIO))
        top_idx = sorted(sorted(scores, key=lambda k: scores[k], reverse=True)[:keep_n])
        return " ".join(sentences[i] for i in top_idx)
