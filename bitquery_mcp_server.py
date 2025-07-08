import config
import bitquery_utils as bq
from mcp.server.fastmcp import FastMCP

WALLET_ADDRESS = config.WALLET_ADDRESS
mcp = FastMCP("BitQuery MCP Server")

@mcp.tool()
def get_trending_tokens():
    """Get trending cryptocurrency tokens."""
    return bq.get_trending_tokens()

@mcp.tool()
def get_wallet_balances():
    """Get wallet balances for configured wallet address."""
    return bq.get_wallet_balances(WALLET_ADDRESS)

@mcp.tool()
def get_marketcap(token_address: str):
    """Get market capitalization data for a token."""
    return bq.get_marketcap(mint_address=token_address)

@mcp.tool()
def get_token_volatility(buy_token: str, sell_token: str):
    """Get volatility data for a token pair."""
    return bq.get_token_volatility(buy_mint=buy_token, sell_mint=sell_token)

@mcp.tool()
def get_top_liquidity_pools():
    """Get top liquidity pools."""
    return bq.get_top_liquidity_pools()

@mcp.tool()
def get_top_holders(token_address: str):
    """Get top holders for a token."""
    return bq.get_top_holders(mint_address=token_address)

@mcp.tool()
def get_trades_of_token(base_token: str, quote_token: str, limit: int = 10):
    """Get trades between two Solana tokens."""
    return bq.get_trades_of_token(base_mint=base_token, quote_mint=quote_token, limit=limit)

@mcp.tool()
def get_ohlcv_custom(
    mint_address: str,
    market_address: str,
    price_asymmetry_lt: float = 0.1,
    limit: int = 10,
    interval_minutes: int = 1
):
    """Get OHLCV data by token mint and market address with price asymmetry filter."""
    return bq.get_ohlcv_by_pair(
        mint_address=mint_address,
        market_address=market_address,
        price_asymmetry_lt=price_asymmetry_lt,
        limit=limit,
        interval_minutes=interval_minutes
    )


if __name__ == "__main__":
    mcp.run()
