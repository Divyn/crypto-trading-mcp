import requests
import json
import os
from dotenv import load_dotenv
import asyncio
from gql import Client, gql
from gql.transport.websockets import WebsocketsTransport
import config
load_dotenv()

BITQUERY_REST_URL = "https://streaming.bitquery.io/eap"
BITQUERY_WS_URL = "wss://streaming.bitquery.io/eap"
BITQUERY_TOKEN = config.BITQUERY_TOKEN
wallet_address = config.WALLET_ADDRESS

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {BITQUERY_TOKEN}"
}

### ----------- REST API Queries ----------- ###

def run_bitquery(query: str, variables: dict = {}):
    payload = json.dumps({
        "query": query,
        "variables": json.dumps(variables)
    })
    response = requests.post(BITQUERY_REST_URL, headers=HEADERS, data=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed with status {response.status_code}: {response.text}")

# 1. Get Top Trending Tokens
def get_trending_tokens():
    query = """
   query TrendingTokens {
  Solana(network: solana, dataset: realtime) {
    DEXTradeByTokens(
      limit: {count: 10}
      orderBy: {descendingByField: "tradesCountWithUniqueTraders"}
      where: {Trade: {Currency: {MintAddress: {notIn: ["So11111111111111111111111111111111111111112","11111111111111111111111111111111"]}}}}
    ) {
      Trade {
        Currency {
          Name
          Symbol
          MintAddress
        }
      }
      tradesCountWithUniqueTraders: count(distinct: Transaction_Signer)
    }
  }
}

    """
    return run_bitquery(query)

# 2. Get Token Volatility
def get_token_volatility(buy_mint: str, sell_mint: str):
    query = """
    query Volatility {
      Solana(dataset: realtime, network: solana) {
        DEXTrades(
          where: {
            Trade: {
              Buy: { Currency: { MintAddress: { is: "%s" } } }
              Sell: { Currency: { MintAddress: { is: "%s" } } }
            }
          }
        ) {
          volatility: standard_deviation(of: Trade_Buy_Price)
        }
      }
    }
    """ % (buy_mint, sell_mint)
    return run_bitquery(query)

# 3. Get Top Liquidity Pools
def get_top_liquidity_pools():
    query = """
    query GetTopPoolsByDex {
      Solana {
        DEXPools(
          orderBy: { descending: Pool_Quote_PostAmount }
          limit: { count: 10 }
        ) {
          Pool {
            Market {
              MarketAddress
              BaseCurrency {
                MintAddress
                Symbol
                Name
              }
              QuoteCurrency {
                MintAddress
                Symbol
                Name
              }
            }
            Dex {
              ProtocolName
              ProtocolFamily
            }
            Quote {
              PostAmount
              PostAmountInUSD
              PriceInUSD
            }
            Base {
              PostAmount
            }
          }
        }
      }
    }
    """
    return run_bitquery(query)

# 4. Get Token Marketcap
def get_marketcap(mint_address: str):
    query = f"""
    query MarketCap {{
      Solana {{
        TokenSupplyUpdates(
          where: {{ TokenSupplyUpdate: {{ Currency: {{ MintAddress: {{ is: "{mint_address}" }} }} }} }}
          limit: {{ count: 1 }}
          orderBy: {{ descending: Block_Time }}
        ) {{
          TokenSupplyUpdate {{
            PostBalanceInUSD
          }}
        }}
      }}
    }}
    """
    return run_bitquery(query)

# 5. Get Wallet Balances
def get_wallet_balances(wallet_address: str):
    query = f"""
    query WalletBalances {{
      Solana {{
        BalanceUpdates(
          where: {{ BalanceUpdate: {{ Account: {{ Owner: {{ is: "{wallet_address}" }} }} }} }}
          orderBy: {{ descendingByField: "BalanceUpdate_Balance_maximum" }}
        ) {{
          BalanceUpdate {{
            Balance: PostBalance(maximum: Block_Slot)
            Currency {{
              Name
              Symbol
            }}
          }}
        }}
      }}
    }}
    """
    return run_bitquery(query)

# 6. Get Top Token Holders
def get_top_holders(mint_address: str):
    query = f"""
    query TopHolders {{
      Solana {{
        BalanceUpdates(
          orderBy: {{ descendingByField: "BalanceUpdate_Holding_maximum" }}
          where: {{
            BalanceUpdate: {{ Currency: {{ MintAddress: {{ is: "{mint_address}" }} }} }}
            Transaction: {{ Result: {{ Success: true }} }}
          }}
        ) {{
          BalanceUpdate {{
            Currency {{
              Name
              MintAddress
              Symbol
            }}
            Account {{
              Address
            }}
            Holding: PostBalance(maximum: Block_Slot, selectWhere: {{ gt: "0" }})
          }}
        }}
      }}
    }}
    """
    return run_bitquery(query)


# 7. Get Latest Trades of a toke

def get_trades_of_token(base_mint: str, quote_mint: str, limit: int = 10):
    query = f"""
    query TokenTrades {{
      Solana(network: solana, dataset: realtime) {{
        DEXTrades(
          limit: {{ count: {limit} }}
          where: {{
            Trade: {{
              Buy: {{ Currency: {{ MintAddress: {{ is: "{base_mint}" }} }} }},
              Sell: {{ Currency: {{ MintAddress: {{ is: "{quote_mint}" }} }} }}
            }}
          }}
          orderBy: {{ descending: Block_Time }}
        ) {{
          Block {{
            Time
          }}
          Transaction {{
            Signature
          }}
          Trade {{
            Buy {{
              Amount
              Currency {{ Symbol }}
            }}
            Sell {{
              Amount
              Currency {{ Symbol }}
            }}
            BuyPrice
          }}
        }}
      }}
    }}
    """
    return run_bitquery(query)


# 10. Get OHLCV Using Pair Address

def get_ohlcv_by_pair(
    mint_address: str,
    market_address: str,
    price_asymmetry_lt: float = 0.1,
    limit: int = 10,
    interval_minutes: int = 1
):
    query = f"""
    query GetOHLCV {{
      Solana {{
        DEXTradeByTokens(
          limit: {{count: {limit}}}
          orderBy: {{descendingByField: "Block_Timefield"}}
          where: {{
            Trade: {{
              Currency: {{ MintAddress: {{ is: "{mint_address}" }} }},
              Market: {{ MarketAddress: {{ is: "{market_address}" }} }},
              PriceAsymmetry: {{ lt: {price_asymmetry_lt} }}
            }}
          }}
        ) {{
          Block {{
            Timefield: Time(interval: {{in: minutes, count: {interval_minutes}}})
          }}
          volume: sum(of: Trade_Amount)
          Trade {{
            high: Price(maximum: Trade_Price)
            low: Price(minimum: Trade_Price)
            open: Price(minimum: Block_Slot)
            close: Price(maximum: Block_Slot)
          }}
          count
        }}
      }}
    }}
    """
    return run_bitquery(query)




### ----------- WebSocket Stream Example ----------- ###

async def subscribe_to_sol_trades():
    token = BITQUERY_TOKEN
    ws_url = f"wss://streaming.bitquery.io/eap?token={token}"

    transport = WebsocketsTransport(
        url=ws_url,
        headers={"Sec-WebSocket-Protocol": "graphql-ws"}
    )

    query = gql("""
    subscription MyQuery {
      Solana {
        DEXTrades {
          Block {
            Time
            Slot
          }
          Transaction {
            Signature
            Index
            Result {
              Success
            }
          }
          Trade {
            Buy {
              Amount
              PriceInUSD
              Currency {
                Symbol
                MintAddress
              }
            }
            Sell {
              Amount
              PriceInUSD
              Currency {
                Symbol
                MintAddress
              }
            }
          }
        }
      }
    }
    """)

    await transport.connect()
    print("Connected to Solana Trade Stream")

    try:
        async for result in transport.subscribe(query):
            print(result)
    except asyncio.CancelledError:
        print("Subscription cancelled.")
    finally:
        await transport.close()
        print("Transport closed")

