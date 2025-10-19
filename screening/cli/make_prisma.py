import argparse, json
from screening.src.prisma_counts import make_prisma


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ta", required=True)
    ap.add_argument("--ft", required=False)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    prisma = make_prisma(args.ta, args.ft)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(prisma, f, ensure_ascii=False, indent=2)
    print(f"Wrote PRISMA counters to {args.out}")

if __name__ == "__main__":
    main()
