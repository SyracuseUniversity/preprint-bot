#!/usr/bin/env python3

import argparse
from preprint_bot.query_arxiv import process_arxiv_category

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse recent arXiv papers by category")
    parser.add_argument("category", help="arXiv subject category (e.g., cs.CL, stat.ML, math.PR)")
    args = parser.parse_args()

    process_arxiv_category(args.category)
