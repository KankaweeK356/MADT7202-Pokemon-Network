from pathlib import Path
import math
import re
import itertools
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

# ---------- Resolve repository paths ----------
CANDIDATES = [
    Path("data/raw/decklists_snapshot.csv"),
    Path("../data/raw/decklists_snapshot.csv"),
]
DATA_PATH = next((p for p in CANDIDATES if p.exists()), None)
if DATA_PATH is None:
    raise FileNotFoundError(
        "Cannot find data/raw/decklists_snapshot.csv. "
        "Run from the repository root, or open the notebook inside notebooks/."
    )

ROOT = DATA_PATH.parents[2]
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

# ---------- Business-aware thresholds ----------
MIN_CARD_PREVALENCE = 0.10
MIN_SHARED_DECKS = 30
JACCARD_CUTOFF = 0.30
MIN_LIFT = 1.20
MIN_SHARED_ARCHETYPES = 3
ROBUSTNESS_JACCARD = [0.25, 0.30, 0.35]

# Declared BEFORE ranking: obvious evolution/mechanical dependencies.
MECHANICAL_PAIRS = {
    tuple(sorted(x)) for x in [
        ("Dreepy", "Drakloak"),
        ("Dreepy", "Dragapult ex"),
        ("Drakloak", "Dragapult ex"),
        ("Dunsparce", "Dudunsparce"),
        ("Duskull", "Dusclops"),
        ("Duskull", "Dusknoir"),
        ("Dusclops", "Dusknoir"),
        ("Abra", "Kadabra"),
        ("Abra", "Alakazam"),
        ("Kadabra", "Alakazam"),
        ("Buneary", "Mega Lopunny ex"),
        ("N's Zorua", "N's Zoroark ex"),
        ("Applin", "Dipplin"),
        ("Riolu", "Mega Lucario ex"),
    ]
}

TOP_WATCHLIST_NODES_FOR_DISPLAY = 5
TOP_PAIR_EDGES_FOR_DISPLAY = 5
MAX_DISPLAY_EDGES_PER_NODE = 2

# ---------- Load frozen snapshot ----------
df = pd.read_csv(DATA_PATH)
N = df["deck_id"].nunique()

print("FROZEN DATASET")
print("Valid decklists:", N)
print("Card-line rows:", len(df))

# Validate 60-card decks.
deck_totals = df.groupby("deck_id")["copies"].sum()
if not deck_totals.eq(60).all():
    bad = deck_totals[~deck_totals.eq(60)]
    raise ValueError(f"Found non-60-card decklists: {bad.head().to_dict()}")

# ---------- Technical cleaning ----------
BASIC = {
    "grass energy", "fire energy", "water energy", "lightning energy",
    "psychic energy", "fighting energy", "darkness energy",
    "metal energy", "fairy energy"
}

def is_basic_energy(name):
    n = re.sub(r"\s+", " ", str(name).strip().lower())
    return (
        n in BASIC
        or (n.startswith("basic ") and n.endswith(" energy"))
        or n.startswith("basic {")
    )

nonbasic = df[~df["card"].map(is_basic_energy)].copy()

deck_card = (
    nonbasic.groupby(["deck_id", "card"], as_index=False)["copies"].sum()
)
deck_card["present"] = 1

presence = (
    deck_card.pivot_table(
        index="deck_id",
        columns="card",
        values="present",
        aggfunc="max",
        fill_value=0
    ).astype(np.uint8)
)

print("\nTECHNICAL CLEANING")
print("Unique non-Basic-Energy cards:", presence.shape[1])
print("Deck x card matrix:", presence.shape)

# ---------- Graph A: raw/pre-pruning network ----------
names_all = presence.columns.tolist()
X_all = presence.to_numpy(dtype=np.int32)
co_all = X_all.T @ X_all

raw_rows = []
for i, a in enumerate(names_all):
    for j in range(i + 1, len(names_all)):
        shared = int(co_all[i, j])
        if shared > 0:
            raw_rows.append((a, names_all[j], shared))

raw_edges = pd.DataFrame(
    raw_rows,
    columns=["card_a", "card_b", "shared_decks"]
)
Graw = nx.from_pandas_edgelist(
    raw_edges, "card_a", "card_b", edge_attr="shared_decks"
)

print("\nGRAPH A — PRE-PRUNING")
print("Nodes:", Graw.number_of_nodes())
print("Edges:", Graw.number_of_edges())

# ---------- Card prevalence ----------
card_counts = presence.sum(axis=0).astype(int)
min_card_decks = math.ceil(MIN_CARD_PREVALENCE * N)
kept = card_counts[card_counts >= min_card_decks].index.tolist()
P = presence[kept].copy()

# Deck -> archetype mapping
deck_arch = (
    df[["deck_id", "archetype"]]
    .drop_duplicates("deck_id")
    .set_index("deck_id")["archetype"]
)

# ---------- Pair metrics ----------
names = P.columns.tolist()
X = P.to_numpy(dtype=np.int32)
co = X.T @ X

pair_rows = []
for i, a in enumerate(names):
    count_a = int(co[i, i])
    for j in range(i + 1, len(names)):
        b = names[j]
        shared = int(co[i, j])
        if shared == 0:
            continue

        count_b = int(co[j, j])
        union = count_a + count_b - shared
        jaccard = shared / union

        p_a = count_a / N
        p_b = count_b / N
        p_ab = shared / N
        lift = p_ab / (p_a * p_b)

        shared_ids = P.index[(P[a] == 1) & (P[b] == 1)]
        breadth = int(deck_arch.loc[shared_ids].nunique())

        pair_rows.append({
            "card_a": a,
            "card_b": b,
            "count_a": count_a,
            "count_b": count_b,
            "shared_decks": shared,
            "jaccard": jaccard,
            "lift": lift,
            "shared_archetypes": breadth,
            "mechanical_pair": tuple(sorted((a, b))) in MECHANICAL_PAIRS,
        })

pairs = pd.DataFrame(pair_rows)

eligible = pairs[
    (pairs["shared_decks"] >= MIN_SHARED_DECKS)
    & (pairs["jaccard"] >= JACCARD_CUTOFF)
    & (pairs["lift"] >= MIN_LIFT)
    & (pairs["shared_archetypes"] >= MIN_SHARED_ARCHETYPES)
    & (~pairs["mechanical_pair"])
].copy().sort_values(
    ["jaccard", "shared_decks", "lift"],
    ascending=[False, False, False]
).reset_index(drop=True)

print("\nSIGNAL REFINEMENT")
print(f"Card prevalence >= 10%: {len(kept)} cards (minimum {min_card_decks} decks)")
print("Eligible business edges:", len(eligible))
print(eligible[
    ["card_a", "card_b", "shared_decks", "jaccard", "lift", "shared_archetypes"]
].head(10).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# ---------- Analysis Graph ----------
G = nx.Graph()
for r in eligible.itertuples(index=False):
    G.add_edge(
        r.card_a, r.card_b,
        jaccard=float(r.jaccard),
        shared_decks=int(r.shared_decks),
        lift=float(r.lift),
        shared_archetypes=int(r.shared_archetypes),
    )

bet = nx.betweenness_centrality(G, normalized=True, weight=None)
weighted_degree = {
    n: sum(d["jaccard"] for _, _, d in G.edges(n, data=True))
    for n in G.nodes()
}
prev = (P.sum(axis=0) / N).to_dict()
deck_count = P.sum(axis=0).astype(int).to_dict()

metrics = pd.DataFrame({
    "card": list(G.nodes()),
    "deck_count": [int(deck_count[n]) for n in G.nodes()],
    "prevalence": [float(prev[n]) for n in G.nodes()],
    "degree": [G.degree(n) for n in G.nodes()],
    "weighted_degree_jaccard": [weighted_degree[n] for n in G.nodes()],
    "betweenness": [bet[n] for n in G.nodes()],
}).sort_values(
    ["weighted_degree_jaccard", "prevalence", "betweenness"],
    ascending=False
).reset_index(drop=True)

print("\nANALYSIS GRAPH")
print("Nodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())
print("Components:", nx.number_connected_components(G))
print(metrics.head(10).to_string(
    index=False,
    formatters={
        "prevalence": "{:.1%}".format,
        "weighted_degree_jaccard": "{:.3f}".format,
        "betweenness": "{:.3f}".format,
    }
))

# ---------- Display backbone (visualization only) ----------
top_watch = metrics.head(TOP_WATCHLIST_NODES_FOR_DISPLAY)["card"].tolist()
top_pairs = eligible.head(TOP_PAIR_EDGES_FOR_DISPLAY)

display_nodes = set(top_watch)
for r in top_pairs.itertuples(index=False):
    display_nodes.add(r.card_a)
    display_nodes.add(r.card_b)

sub_edges = eligible[
    eligible["card_a"].isin(display_nodes)
    & eligible["card_b"].isin(display_nodes)
].copy()

display_keep = set()
for n in display_nodes:
    s = sub_edges[
        (sub_edges["card_a"] == n) | (sub_edges["card_b"] == n)
    ].sort_values(
        ["jaccard", "shared_decks", "lift"],
        ascending=[False, False, False]
    ).head(MAX_DISPLAY_EDGES_PER_NODE)

    for r in s.itertuples(index=False):
        display_keep.add(tuple(sorted((r.card_a, r.card_b))))

display_edges = sub_edges[
    sub_edges.apply(
        lambda r: tuple(sorted((r["card_a"], r["card_b"]))) in display_keep,
        axis=1
    )
].copy()

Gdisp = nx.Graph()
for r in display_edges.itertuples(index=False):
    Gdisp.add_edge(
        r.card_a, r.card_b,
        jaccard=float(r.jaccard),
        shared_decks=int(r.shared_decks),
        lift=float(r.lift),
        shared_archetypes=int(r.shared_archetypes)
    )

print("\nDISPLAY BACKBONE")
print("Nodes:", Gdisp.number_of_nodes())
print("Edges:", Gdisp.number_of_edges())
print("NOTE: centrality metrics were computed on the Analysis Graph, not this display graph.")

# ---------- Robustness ----------
best = eligible.iloc[0]
best_key = tuple(sorted((best["card_a"], best["card_b"])))
rob_rows = []

for cut in ROBUSTNESS_JACCARD:
    ed = pairs[
        (pairs["shared_decks"] >= MIN_SHARED_DECKS)
        & (pairs["jaccard"] >= cut)
        & (pairs["lift"] >= MIN_LIFT)
        & (pairs["shared_archetypes"] >= MIN_SHARED_ARCHETYPES)
        & (~pairs["mechanical_pair"])
    ].copy()

    gg = nx.Graph()
    for r in ed.itertuples(index=False):
        gg.add_edge(r.card_a, r.card_b)

    survives = any(
        tuple(sorted((r.card_a, r.card_b))) == best_key
        for r in ed.itertuples(index=False)
    )

    rob_rows.append({
        "jaccard_cutoff": cut,
        "nodes": gg.number_of_nodes(),
        "edges": gg.number_of_edges(),
        "components": nx.number_connected_components(gg) if gg.number_of_nodes() else 0,
        "top_pair_survives": survives,
    })

robustness = pd.DataFrame(rob_rows)
print("\nROBUSTNESS")
print(robustness.to_string(index=False))

# ---------- Save reproducible outputs ----------
raw_edges.to_csv(OUT / "raw_graph_edges.csv", index=False)
eligible.to_csv(OUT / "analysis_edges.csv", index=False)
metrics.to_csv(OUT / "node_metrics.csv", index=False)
display_edges.to_csv(OUT / "display_edges.csv", index=False)
robustness.to_csv(OUT / "robustness.csv", index=False)

# ---------- Notebook graph ----------
plt.figure(figsize=(13, 8))
pos = nx.spring_layout(Gdisp, seed=42, weight="jaccard", k=1.4, iterations=100)

node_sizes = [900 + 3500 * float(prev.get(n, 0)) for n in Gdisp.nodes()]
edge_widths = [1.5 + 7 * Gdisp[u][v]["jaccard"] for u, v in Gdisp.edges()]

nx.draw_networkx_nodes(Gdisp, pos, node_size=node_sizes, alpha=0.92)
nx.draw_networkx_edges(Gdisp, pos, width=edge_widths, alpha=0.42)
nx.draw_networkx_labels(Gdisp, pos, font_size=9)

plt.title(
    "Actionable Stock Network\n"
    f"Analysis Graph: {G.number_of_nodes()} nodes / {G.number_of_edges()} edges | "
    f"Display: {Gdisp.number_of_nodes()} nodes / {Gdisp.number_of_edges()} edges"
)
plt.axis("off")
plt.tight_layout()
plt.savefig(OUT / "actionable_network_from_notebook.png", dpi=220, bbox_inches="tight")
plt.show()

# ---------- A4-ready findings ----------
watch = metrics.iloc[0]
print("\nA4-READY FINDINGS")
print(
    f"Graph reduction: Raw {Graw.number_of_nodes()}/{Graw.number_of_edges()} -> "
    f"Analysis {G.number_of_nodes()}/{G.number_of_edges()} -> "
    f"Display {Gdisp.number_of_nodes()}/{Gdisp.number_of_edges()} (nodes/edges)"
)
print(
    f"Core Watchlist: {watch['card']} | {int(watch['deck_count'])}/{N} decks "
    f"({watch['prevalence']:.1%}) | WD={watch['weighted_degree_jaccard']:.3f} | "
    f"Betweenness={watch['betweenness']:.3f}"
)
print(
    f"Pair-check: {best['card_a']} — {best['card_b']} | "
    f"shared={int(best['shared_decks'])} | Jaccard={best['jaccard']:.3f} | "
    f"Lift={best['lift']:.3f} | breadth={int(best['shared_archetypes'])}"
)
