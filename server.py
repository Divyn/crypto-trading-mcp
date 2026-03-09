import logging
import os

from dotenv import load_dotenv

load_dotenv()

# Reduce noisy MCP/httpx logs (e.g. "Processing request..." and HTTP request dumps)
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

from openai import OpenAI
import bitquery_utils as bq
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response
from mcp.server.sse import SseServerTransport

mcp = FastMCP("BitQuery MCP Server")

transport = SseServerTransport("/messages/")


async def handle_sse(request):
    async with transport.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (in_stream, out_stream):
        await mcp._mcp_server.run(
            in_stream,
            out_stream,
            mcp._mcp_server.create_initialization_options(),
        )
    return Response()


sse_app = Starlette(
    routes=[
        Route("/sse", handle_sse, methods=["GET"]),
        Mount("/messages/", app=transport.handle_post_message),
    ]
)

app = FastAPI()


@app.get("/health")
def health():
    return {"message": "MCP SSE Server is running"}


app.mount("/", sse_app)

SYSTEM_PROMPT = """You are a Bitquery GraphQL expert for Solana blockchain data.
Your job is to convert natural language questions into valid Bitquery GraphQL queries.

Return ONLY the raw GraphQL query string — no explanation, no markdown, no code blocks.

Bitquery API endpoint: https://streaming.bitquery.io/eap

Key schema patterns to follow:

1. Trending tokens:
query TrendingTokens {
  Solana(network: solana, dataset: realtime) {
    DEXTradeByTokens(
      limit: {count: 10}
      orderBy: {descendingByField: "tradesCountWithUniqueTraders"}
      where: {Trade: {Currency: {MintAddress: {notIn: ["So11111111111111111111111111111111111111112"]}}}}
    ) {
      Trade { Currency { Name Symbol MintAddress } }
      tradesCountWithUniqueTraders: count(distinct: Transaction_Signer)
    }
  }
}

2. OHLCV by token + market:
query GetOHLCV {
  Solana {
    DEXTradeByTokens(
      limit: {count: 10}
      orderBy: {descendingByField: "Block_Timefield"}
      where: {
        Trade: {
          Currency: { MintAddress: { is: "<MINT>" } }
          Market: { MarketAddress: { is: "<MARKET>" } }
          PriceAsymmetry: { lt: 0.1 }
        }
      }
    ) {
      Block { Timefield: Time(interval: {in: minutes, count: 1}) }
      volume: sum(of: Trade_Amount)
      Trade {
        high: Price(maximum: Trade_Price)
        low: Price(minimum: Trade_Price)
        open: Price(minimum: Block_Slot)
        close: Price(maximum: Block_Slot)
      }
      count
    }
  }
}

3. OHLC via Trading API (USD values):
query SolanaTokenOHLC {
  Trading {
    Tokens(
      limit: {count: 10}
      where: {
        Interval: {Time: {Duration: {eq: 1}}}
        Token: { Network: {is: "solana"} Address: {is: "<MINT>"} }
      }
      orderBy: {descending: Interval_Time_Start}
    ) {
      Token { Address Name Symbol Network }
      Interval { Time { Start Duration End } }
      Volume { Base Quote Usd }
      Price {
        IsQuotedInUsd
        Ohlc { Close High Low Open }
      }
    }
  }
}

4. Top holders:
query TopHolders {
  Solana {
    BalanceUpdates(
      orderBy: {descendingByField: "BalanceUpdate_Holding_maximum"}
      where: {
        BalanceUpdate: { Currency: { MintAddress: { is: "<MINT>" } } }
        Transaction: { Result: { Success: true } }
      }
    ) {
      BalanceUpdate {
        Currency { Name MintAddress Symbol }
        Account { Address }
        Holding: PostBalance(maximum: Block_Slot, selectWhere: {gt: "0"})
      }
    }
  }
}

5. DEX trades between two tokens:
query TokenTrades {
  Solana(network: solana, dataset: realtime) {
    DEXTrades(
      limit: {count: 10}
      where: {
        Trade: {
          Buy: { Currency: { MintAddress: { is: "<BASE_MINT>" } } }
          Sell: { Currency: { MintAddress: { is: "<QUOTE_MINT>" } } }
        }
      }
      orderBy: {descending: Block_Time}
    ) {
      Block { Time }
      Transaction { Signature }
      Trade {
        Buy { Amount Currency { Symbol } }
        Sell { Amount Currency { Symbol } }
        BuyPrice
      }
    }
  }
}

6. Token market cap:
query MarketCap {
  Solana {
    TokenSupplyUpdates(
      where: { TokenSupplyUpdate: { Currency: { MintAddress: { is: "<MINT>" } } } }
      limit: {count: 1}
      orderBy: {descending: Block_Time}
    ) {
      TokenSupplyUpdate { PostBalanceInUSD }
    }
  }
}

7. Wallet balances:
query WalletBalances {
  Solana {
    BalanceUpdates(
      where: { BalanceUpdate: { Account: { Owner: { is: "<WALLET_ADDRESS>" } } } }
      orderBy: {descendingByField: "BalanceUpdate_Balance_maximum"}
    ) {
      BalanceUpdate {
        Balance: PostBalance(maximum: Block_Slot)
        Currency { Name Symbol }
      }
    }
  }
}

8. Top liquidity pools:
query GetTopPools {
  Solana {
    DEXPools(
      orderBy: {descending: Pool_Quote_PostAmount}
      limit: {count: 10}
    ) {
      Pool {
        Market {
          MarketAddress
          BaseCurrency { MintAddress Symbol Name }
          QuoteCurrency { MintAddress Symbol Name }
        }
        Dex { ProtocolName ProtocolFamily }
        Quote { PostAmount PostAmountInUSD PriceInUSD }
        Base { PostAmount }
      }
    }
  }
}

9. Token volatility:
query Volatility {
  Solana(dataset: realtime, network: solana) {
    DEXTrades(
      where: {
        Trade: {
          Buy: { Currency: { MintAddress: { is: "<BUY_MINT>" } } }
          Sell: { Currency: { MintAddress: { is: "<SELL_MINT>" } } }
        }
      }
    ) {
      volatility: standard_deviation(of: Trade_Buy_Price)
    }
  }
}
"""

OUTPUT_FORMAT_PROMPT = """You are a helpful assistant that presents blockchain data clearly.

The user asked a question about Solana data. You have received the raw JSON response from the Bitquery API.

Your job: turn this data into a clear, human-friendly answer. Follow any format the user requested (e.g. "as a table", "summarize", "list"). If they said "table" or "share as table", render the data as a markdown table. Otherwise pick the best format (table for lists of items, short summary for single values). Be concise. Do not repeat the raw JSON."""


@mcp.tool()
def ask_bitquery(question: str) -> dict:
    """
    Ask any question about Solana on-chain data in plain English.
    The server generates the Bitquery GraphQL query, runs it, then formats the result
    into a clear answer (e.g. table or summary).

    Examples:
      - "Get trending tokens on Solana"
      - "Top tokens in solana, share as table"
      - "Show top 10 holders of token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
      - "What is the market cap of <mint>?"

    Args:
        question: Plain English description of the data you want from Bitquery.
    """
    import json
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Step 1: question -> LLM -> GraphQL query
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
    )

    query = response.choices[0].message.content.strip()
    if query.startswith("```"):
        query = "\n".join(
            line for line in query.splitlines()
            if not line.strip().startswith("```")
        ).strip()

    # Step 2: run query -> raw output
    raw = bq.run_bitquery(query)

    # Step 3: raw output + question -> LLM -> formatted meaningful output
    raw_str = json.dumps(raw, indent=2)
    format_response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": OUTPUT_FORMAT_PROMPT},
            {"role": "user", "content": f"User question: {question}\n\nRaw API response:\n{raw_str}"}
        ]
    )
    formatted = format_response.choices[0].message.content.strip()

    return {"answer": formatted}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8100))
    print(f"Running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
