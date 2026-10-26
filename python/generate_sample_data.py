"""Create a small synthetic dataset with the SAME schema as the Kaggle REES46 files.
Use it to test the pipeline without downloading ~14 GB.   python generate_sample_data.py --users 6000
"""
import argparse, os, uuid
import numpy as np, pandas as pd

CATS = {  # category_code: (median price, brands)
 "electronics.smartphone": (320, ["apple","samsung","xiaomi","huawei"]),
 "electronics.audio.headphone": (60, ["sony","jbl","xiaomi","apple"]),
 "appliances.kitchen.kettle": (35, ["bosch","philips","tefal"]),
 "apparel.shoes": (55, ["nike","adidas","puma"]),
 "furniture.living_room.chair": (90, ["ikea","hoff"]),
 "computers.notebook": (650, ["lenovo","asus","hp","apple"]),
 "kids.toys": (18, ["lego","mattel","hasbro"]),
 "accessories.bag": (40, ["samsonite","xiaomi","nike"]),
}
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--users", type=int, default=6000)
    ap.add_argument("--out", default="../data/sample"); ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(); rng = np.random.default_rng(a.seed); os.makedirs(a.out, exist_ok=True)
    start, end = pd.Timestamp("2019-10-01", tz="UTC"), pd.Timestamp("2020-05-01", tz="UTC")
    span = (end - start).days; cats = list(CATS); rows = []
    for _ in range(a.users):
        uid = int(rng.integers(5e8, 6e8)); join = int(min(rng.exponential(60), span - 1))
        life = join + rng.exponential(rng.choice([25, 70, 160]))       # when the customer fades out
        rate = rng.gamma(2, 0.35) + 0.05                                # sessions per week at peak
        psens = rng.beta(2, 3); p_buy = rng.beta(2, 8) + 0.02          # price sensitivity, buy propensity
        fav = rng.choice(cats, size=2, replace=False)
        day = join
        while day < min(life, span):
            fade = max(0.05, 1 - max(0, day - (life - 40)) / 40)         # activity decays before leaving
            if rng.random() < rate / 7 * fade:
                sid = str(uuid.UUID(int=int(rng.integers(0, 2**62)) << 64 | int(rng.integers(0, 2**62))))
                t = start + pd.Timedelta(days=day, seconds=int(rng.integers(0, 86000)))
                cat = rng.choice(fav) if rng.random() < .7 else rng.choice(cats)
                med, brands = CATS[cat]; carted = []
                for k in range(int(rng.integers(1, 9))):
                    price = round(float(med * rng.lognormal(0, .35) * (1 - .35 * psens * rng.random())), 2)
                    pid = int(rng.integers(1e6, 1e6 + 4000)); brand = rng.choice(brands); t += pd.Timedelta(seconds=int(rng.integers(5, 240)))
                    base = (t, "view", pid, 2e18 + cats.index(cat), cat if rng.random() > .08 else None, brand, price, uid, sid); rows.append(base)
                    if rng.random() < .22 * (1 + p_buy):
                        t += pd.Timedelta(seconds=30); rows.append((t, "cart") + base[2:]); carted.append(base)
                        if rng.random() < .15: t += pd.Timedelta(seconds=20); rows.append((t, "remove_from_cart") + base[2:]); carted.pop()
                if carted and rng.random() < p_buy * 3.2:
                    for b in carted: t += pd.Timedelta(seconds=60); rows.append((t, "purchase") + b[2:])
            day += 1
    df = pd.DataFrame(rows, columns=["event_time","event_type","product_id","category_id","category_code","brand","price","user_id","user_session"])
    df["category_id"] = df["category_id"].astype("int64")
    df = df[df.event_time < end].sort_values("event_time")
    for m, g in df.groupby(df.event_time.dt.strftime("%Y-%b")):
        g = g.copy(); g["event_time"] = g.event_time.dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        g.to_csv(os.path.join(a.out, f"{m}.csv"), index=False)
    print(f"{len(df):,} events, {df.user_id.nunique():,} users, files in {a.out}:", sorted(os.listdir(a.out)))
if __name__ == "__main__": main()
