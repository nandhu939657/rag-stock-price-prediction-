"""One-off script: populate strategy_knowledge with original summaries of core
principles from well-known investing/trading books, embed them, and insert into
Supabase. Run once (or whenever STRATEGIES below changes):

    cd backend
    ./venv/Scripts/python.exe scripts/seed_strategy_knowledge.py

Every entry below is an ORIGINAL summary written for this app, not verbatim text from
any book - it describes the well-known, widely-taught principle associated with that
book/author (the kind of thing covered in any finance course or investing article),
attributed for context. Books were chosen for a deliberately diverse spread of
philosophies (value, growth, technical, momentum, psychology, risk management, and
passive/efficient-market views) so RAG retrieval has good material to match against
very different technical situations.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow `python scripts/seed_strategy_knowledge.py`

from app.db.supabase_client import get_supabase
from app.ingestion.embeddings import embed_texts

STRATEGIES: list[dict[str, str]] = [
    # --- The Intelligent Investor, Benjamin Graham ---
    {
        "book_title": "The Intelligent Investor",
        "author": "Benjamin Graham",
        "topic": "value_investing",
        "content": (
            "Margin of safety: only buy when the price is meaningfully below your estimate of a company's "
            "intrinsic value, so errors in judgment or bad luck don't wipe out the investment. The larger the "
            "gap between price and estimated value, the more protection the investor has against being wrong."
        ),
    },
    {
        "book_title": "The Intelligent Investor",
        "author": "Benjamin Graham",
        "topic": "psychology",
        "content": (
            "The Mr. Market allegory: treat daily price swings as an emotional business partner who offers to "
            "buy or sell every day at a different, often irrational price. His mood swings are opportunities to "
            "exploit when convenient, not signals to follow - short-term price action that disagrees with a "
            "careful valuation should usually be ignored rather than chased."
        ),
    },
    {
        "book_title": "The Intelligent Investor",
        "author": "Benjamin Graham",
        "topic": "risk_management",
        "content": (
            "Know whether you are a defensive or enterprising investor. A defensive investor should diversify "
            "broadly and avoid trying to time or pick individual winners. An enterprising investor willing to do "
            "real research can seek mispriced securities, but only with real discipline and a margin of safety - "
            "half-hearted effort in either style tends to underperform both."
        ),
    },
    # --- Security Analysis, Graham & Dodd ---
    {
        "book_title": "Security Analysis",
        "author": "Benjamin Graham and David Dodd",
        "topic": "value_investing",
        "content": (
            "A stock's worth should be estimated from durable fundamentals - earnings power, assets, and "
            "balance sheet strength - not from price momentum or popularity. Price and intrinsic value can "
            "diverge for long stretches, and the fundamentals-based estimate is what should anchor a decision."
        ),
    },
    {
        "book_title": "Security Analysis",
        "author": "Benjamin Graham and David Dodd",
        "topic": "risk_management",
        "content": (
            "Prioritize quantitative safety before growth potential: favor companies with low debt, consistent "
            "earnings history, and adequate asset coverage. Capital preservation comes first - a cheap stock "
            "with a fragile balance sheet is a value trap, not a bargain."
        ),
    },
    # --- Common Stocks and Uncommon Profits, Philip Fisher ---
    {
        "book_title": "Common Stocks and Uncommon Profits",
        "author": "Philip Fisher",
        "topic": "fundamental_analysis",
        "content": (
            "The 'scuttlebutt' method: qualitative research - talking to customers, competitors, suppliers, and "
            "employees - can reveal a company's real competitive position and management quality better than "
            "financial statements alone. Numbers show what happened; scuttlebutt helps explain why and whether "
            "it will continue."
        ),
    },
    {
        "book_title": "Common Stocks and Uncommon Profits",
        "author": "Philip Fisher",
        "topic": "growth_investing",
        "content": (
            "Once a genuinely superior company with a durable competitive edge and capable management has been "
            "found, resist the urge to sell on minor price dips or short-term news. Long holding periods let "
            "compounding growth do the work that trading in and out cannot."
        ),
    },
    # --- One Up On Wall Street, Peter Lynch ---
    {
        "book_title": "One Up On Wall Street",
        "author": "Peter Lynch",
        "topic": "fundamental_analysis",
        "content": (
            "Everyday observations - a product you love, a store that's always crowded - can be a legitimate "
            "investing edge, but only when followed up with real fundamental research. The observation is a "
            "starting point for investigation, never a substitute for it."
        ),
    },
    {
        "book_title": "One Up On Wall Street",
        "author": "Peter Lynch",
        "topic": "growth_investing",
        "content": (
            "Classify a stock by type - slow grower, stalwart, fast grower, cyclical, turnaround, or asset play "
            "- before valuing it. A fair P/E ratio for a fast grower should roughly track its earnings growth "
            "rate (the PEG concept); paying a fast-grower multiple for a slow grower is a common mistake."
        ),
    },
    # --- How to Make Money in Stocks (CANSLIM), William O'Neil ---
    {
        "book_title": "How to Make Money in Stocks",
        "author": "William O'Neil",
        "topic": "growth_investing",
        "content": (
            "The CANSLIM framework screens for: Current strong quarterly earnings growth, Annual earnings growth "
            "over several years, a New product/management/price high acting as a catalyst, Supply and demand "
            "shown by rising volume on up moves, Leadership versus laggards in its industry, increasing "
            "Institutional sponsorship, and overall Market direction confirmed in an uptrend."
        ),
    },
    {
        "book_title": "How to Make Money in Stocks",
        "author": "William O'Neil",
        "topic": "risk_management",
        "content": (
            "Cut losses fast and mechanically: sell any position that falls roughly 7-8% below the purchase "
            "price, without exceptions or hoping for a recovery. Protecting capital from large losses matters "
            "more than being right on any single trade."
        ),
    },
    # --- Technical analysis classics (Murphy / Pring synthesis) ---
    {
        "book_title": "Technical Analysis of the Financial Markets",
        "author": "John J. Murphy",
        "topic": "trend_following",
        "content": (
            "The trend is the dominant force: identify the prevailing trend using moving averages or trendlines "
            "and trade in its direction rather than trying to pick exact tops and bottoms. Most of a stock's "
            "total move happens while an established trend is intact, not at its turning points."
        ),
    },
    {
        "book_title": "Technical Analysis Explained",
        "author": "Martin J. Pring",
        "topic": "technical_analysis",
        "content": (
            "Support and resistance act as market memory: prior price levels where a stock repeatedly reversed "
            "become psychological barriers. A breakout above resistance or breakdown below support on strong "
            "volume often signals genuine continuation rather than a false move."
        ),
    },
    {
        "book_title": "Technical Analysis Explained",
        "author": "Martin J. Pring",
        "topic": "technical_analysis",
        "content": (
            "Volume should confirm price: a price move accompanied by high volume is more likely genuine and "
            "sustainable than the same move on low volume, which often signals a lack of real conviction behind "
            "the move and a higher chance of reversal."
        ),
    },
    # --- Reminiscences of a Stock Operator (Jesse Livermore), Edwin Lefèvre ---
    {
        "book_title": "Reminiscences of a Stock Operator",
        "author": "Edwin Lefèvre (chronicling Jesse Livermore)",
        "topic": "risk_management",
        "content": (
            "The single biggest source of losses was refusing to admit being wrong quickly, while the biggest "
            "gains came from staying in a position as long as the trend continued favorably. Cut losing trades "
            "fast; let winning trades run rather than taking small profits out of impatience or fear."
        ),
    },
    {
        "book_title": "Reminiscences of a Stock Operator",
        "author": "Edwin Lefèvre (chronicling Jesse Livermore)",
        "topic": "trend_following",
        "content": (
            "Trade the line of least resistance: rather than predicting exactly where a stock will go, watch "
            "which direction it moves most easily under pressure and align with that path instead of fighting "
            "it with a predetermined opinion."
        ),
    },
    {
        "book_title": "Reminiscences of a Stock Operator",
        "author": "Edwin Lefèvre (chronicling Jesse Livermore)",
        "topic": "psychology",
        "content": (
            "Markets rhyme rather than repeat exactly: human psychology - greed, fear, hope - drives recurring "
            "patterns of speculation and panic across market cycles, even though the specific companies and "
            "headlines differ every time."
        ),
    },
    # --- Trading in the Zone, Mark Douglas ---
    {
        "book_title": "Trading in the Zone",
        "author": "Mark Douglas",
        "topic": "psychology",
        "content": (
            "Think in probabilities, not certainties: no single trade's outcome can be known in advance. A "
            "sound strategy applied consistently across many trades will produce a statistical edge over time, "
            "even though individual trades will still lose - judging a strategy by one outcome is a mistake."
        ),
    },
    {
        "book_title": "Trading in the Zone",
        "author": "Mark Douglas",
        "topic": "psychology",
        "content": (
            "Only take a position whose potential loss has genuinely been accepted before entering. Hesitation "
            "or panic when a loss develops - rather than following a predefined plan - is a leading cause of "
            "poor decisions and larger-than-intended losses."
        ),
    },
    # --- Market Wizards (interview series), Jack Schwager ---
    {
        "book_title": "Market Wizards",
        "author": "Jack D. Schwager",
        "topic": "risk_management",
        "content": (
            "Across interviews with traders of very different styles, one theme was near-universal: controlling "
            "position size and predefining an exit before entering a trade mattered more to long-term success "
            "than trying to maximize the return on any single trade."
        ),
    },
    {
        "book_title": "Market Wizards",
        "author": "Jack D. Schwager",
        "topic": "psychology",
        "content": (
            "There is no single 'best' strategy. Top performers found an approach - trend following, mean "
            "reversion, fundamental, or quantitative - that fit their own temperament and stuck with it through "
            "inevitable losing streaks, rather than switching styles after every setback."
        ),
    },
    # --- A Random Walk Down Wall Street, Burton Malkiel ---
    {
        "book_title": "A Random Walk Down Wall Street",
        "author": "Burton G. Malkiel",
        "topic": "market_efficiency",
        "content": (
            "Markets are largely efficient: publicly available information is usually reflected in price "
            "quickly, so consistently beating the market through stock-picking or timing is difficult even for "
            "professional investors. This is a reason for humility about any single prediction, not a reason to "
            "ignore fundamentals entirely."
        ),
    },
    {
        "book_title": "A Random Walk Down Wall Street",
        "author": "Burton G. Malkiel",
        "topic": "passive_investing",
        "content": (
            "A broadly diversified, low-cost portfolio held over the long term has historically outperformed "
            "most actively managed attempts to beat it, after fees are accounted for - diversification reduces "
            "the damage any single bad pick can do to a portfolio."
        ),
    },
    # --- The Little Book of Common Sense Investing, John Bogle ---
    {
        "book_title": "The Little Book of Common Sense Investing",
        "author": "John C. Bogle",
        "topic": "passive_investing",
        "content": (
            "Costs compound against an investor over time: even small differences in fees and portfolio "
            "turnover compound dramatically over decades. Minimizing costs is one of the few variables in "
            "investing genuinely within an investor's control."
        ),
    },
    {
        "book_title": "The Little Book of Common Sense Investing",
        "author": "John C. Bogle",
        "topic": "psychology",
        "content": (
            "Reacting emotionally to short-term volatility by trading in and out of positions has historically "
            "cost investors more than the volatility itself. Staying the course through downturns, rather than "
            "panic-selling near lows, is consistently associated with better long-term outcomes."
        ),
    },
    # --- Quantitative Momentum, Gray & Vogel ---
    {
        "book_title": "Quantitative Momentum",
        "author": "Wesley R. Gray and Jack R. Vogel",
        "topic": "momentum",
        "content": (
            "Momentum is a historically persistent factor: stocks that outperformed over the past 3-12 months "
            "have tended to keep outperforming over the following few months more often than chance would "
            "predict - though the effect is noisy and prone to sharp, sudden reversals ('momentum crashes')."
        ),
    },
    {
        "book_title": "Quantitative Momentum",
        "author": "Wesley R. Gray and Jack R. Vogel",
        "topic": "momentum",
        "content": (
            "Raw momentum performs better when combined with basic quality and risk filters - avoiding highly "
            "volatile, low-liquidity, or fundamentally deteriorating stocks - rather than simply chasing "
            "whichever name has the single highest recent return."
        ),
    },
    # --- Trade Your Way to Financial Freedom, Van Tharp ---
    {
        "book_title": "Trade Your Way to Financial Freedom",
        "author": "Van K. Tharp",
        "topic": "risk_management",
        "content": (
            "Position sizing - how much capital is risked per trade - has a larger effect on long-term account "
            "growth and survival than which specific stock or exact entry point is chosen. Two traders with the "
            "same signals can have opposite outcomes purely from differing position sizing discipline."
        ),
    },
    {
        "book_title": "Trade Your Way to Financial Freedom",
        "author": "Van K. Tharp",
        "topic": "risk_management",
        "content": (
            "Before trading a strategy with real capital, understand its historical expectancy - average win "
            "size times win rate, minus average loss size times loss rate - so that position sizing decisions "
            "are grounded in real numbers rather than hope or a recent hot streak."
        ),
    },
    # --- Trade Like a Stock Market Wizard, Mark Minervini ---
    {
        "book_title": "Trade Like a Stock Market Wizard",
        "author": "Mark Minervini",
        "topic": "risk_management",
        "content": (
            "Cap losses at a small, predefined percentage on every single trade, so that a handful of large "
            "winners can outweigh many small, controlled losses over time. The goal is not to be right often - "
            "it's to lose small when wrong and win big when right."
        ),
    },
    {
        "book_title": "Trade Like a Stock Market Wizard",
        "author": "Mark Minervini",
        "topic": "momentum",
        "content": (
            "Favor stocks already showing relative strength versus the broader market and basing near recent "
            "highs, rather than stocks that look cheap because they are falling. In the right market conditions, "
            "strength tends to beget further strength more reliably than a falling knife recovers."
        ),
    },
]


def main() -> None:
    supabase = get_supabase()

    existing = supabase.table("strategy_knowledge").select("id", count="exact").execute()
    if existing.count:
        print(f"strategy_knowledge already has {existing.count} rows - clearing before reseeding.")
        supabase.table("strategy_knowledge").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    print(f"Embedding {len(STRATEGIES)} strategy principles...")
    embeddings = embed_texts([s["content"] for s in STRATEGIES])

    rows = [{**s, "embedding": emb} for s, emb in zip(STRATEGIES, embeddings)]
    supabase.table("strategy_knowledge").insert(rows).execute()

    books = sorted({s["book_title"] for s in STRATEGIES})
    print(f"Inserted {len(rows)} principles from {len(books)} books:")
    for b in books:
        print(f"  - {b}")


if __name__ == "__main__":
    main()
