"""GRU corrector: learns departure-timing deviation from the June register.

The corrector forecasts next-day mean departure deviation per lane from
a 7-day window of lane-day features, to replace the optimiser's
zero-deviation assumption. Evaluation is deliberately adversarial:
the model is compared against per-lane-mean and persistence baselines,
because one month of low-variance actuals (within-lane std 0.15 days)
may not reward sequence learning - an honest finding either way, with
the architecture justified by extensibility to further monthly
registers rather than by June alone.
"""

import numpy as np
import pandas as pd
import torch
from torch import nn

from src.data.build import fact_shipments

MIN_SHIPMENTS = 20
WINDOW = 7

def build_panel():
    """Lane-day panel for the nine lanes with >= 20 June shipments."""
    s = fact_shipments()
    s["day"] = s["created_ts"].dt.normalize()
    keep = s.groupby("lane_id").size()
    lanes = sorted(keep[keep >= MIN_SHIPMENTS].index)
    days = pd.date_range(s["day"].min(), s["day"].max(), freq="D")
    frames = []
    for lane in lanes:
        g = s[s["lane_id"] == lane].groupby("day").agg(
            n=("qty", "size"), units=("qty", "sum"),
            dev=("dep_deviation_days", "mean"),
            lag=("customs_lag_days", "mean"))
        g = g.reindex(days)
        g[["n", "units"]] = g[["n", "units"]].fillna(0)
        g["dev"] = g["dev"].ffill()
        g["lane_id"] = lane
        g["weekday"] = g.index.dayofweek
        frames.append(g.reset_index(names="day"))
    return pd.concat(frames, ignore_index=True), lanes, days


def build_sequences(panel, lanes, days):
    """Sliding 7-day windows -> next-day mean deviation per lane."""
    X, y, meta = [], [], []
    for li, lane in enumerate(lanes):
        g = panel[panel["lane_id"] == lane].reset_index(drop=True)
        feats = np.column_stack([
            g["n"].to_numpy(float),
            g["units"].to_numpy(float) / 1000.0,
            g["dev"].to_numpy(float),
            np.sin(2 * np.pi * g["weekday"] / 7),
            np.cos(2 * np.pi * g["weekday"] / 7),
        ])
        target = g["dev"].to_numpy(float)
        for t in range(WINDOW, len(g)):
            window = feats[t - WINDOW:t]
            if np.isnan(window).any() or np.isnan(target[t]):
                continue
            X.append(window)
            y.append(target[t])
            meta.append((li, t))
    return np.array(X), np.array(y), np.array(meta)


def train_val_split(meta, days, frac=0.7):
    split_day = int(len(days) * frac)
    train = meta[:, 1] <= split_day
    return train, ~train


def baseline_maes(X, y, meta, train, val, lanes):
    """The three predictors the GRU has to justify itself against."""
    lane_means = {li: y[train & (meta[:, 0] == li)].mean()
                  for li in range(len(lanes)) if (train & (meta[:, 0] == li)).any()}
    fallback = y[train].mean()
    naive = np.array([lane_means.get(li, fallback) for li in meta[val][:, 0]])
    return {
        "global_mean": float(np.abs(y[val] - fallback).mean()),
        "lane_mean": float(np.abs(y[val] - naive).mean()),
        "persistence": float(np.abs(y[val] - X[val][:, -1, 2]).mean()),
    }


class GRUCorrector(nn.Module):
    def __init__(self, n_features=5, hidden=16):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        return self.head(out[:, -1]).squeeze(-1)


def train_model(X, y, train_mask, seed=1, epochs=300, hidden=16, lr=0.01):
    torch.manual_seed(seed)
    flat = X[train_mask].reshape(-1, X.shape[-1])
    mu, sd = flat.mean(axis=0), flat.std(axis=0) + 1e-8
    Xt = torch.tensor((X - mu) / sd, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32)
    tm = torch.tensor(train_mask)

    model = GRUCorrector(X.shape[-1], hidden)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.L1Loss()
    history = []
    for _ in range(epochs):
        model.train()
        optimiser.zero_grad()
        loss = loss_fn(model(Xt[tm]), yt[tm])
        loss.backward()
        optimiser.step()
        optimiser.zero_grad()
        history.append(float(loss.detach()))
    model.eval()
    with torch.no_grad():
        predictions = model(Xt).numpy()
    return model, predictions, history