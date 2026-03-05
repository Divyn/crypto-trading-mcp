# Building an MCP with Claude for Solana Trade Data

Video Tutorial [here](https://youtu.be/q-QL5EGfT5k)

## Prerequisites

* A Bitquery account. Sign up [here](http://ide.bitquery.io/).
* Claude desktop installed for your operating system.
* Ability to code in Python (or another language you’re comfortable with).

## Accessing Data & APIs

* Most common APIs and data points are available as examples in Bitquery’s documentation.
* You can copy Markdown pages directly from the [documentation](https://github.com/bitquery/streaming-data-platform-docs).
* Support for queries, APIs, and data streams across multiple chains (Bitcoin, Solana, Tron, EVM chains) is available via Telegram or support tickets.

## Building the MCP

* This code contains utilities file to connect to the Bitquery API and fetch data.
* Each data point is implemented as a separate function.
* The Fast MCP library is used to set up the MCP server.
* MCP functions are created to call these data-point functions and return results.

## Calling the Bitquery API

* Calling the API is straightforward: pass the query to the endpoint along with [your bearer token](https://docs.bitquery.io/docs/authorisation/how-to-generate/).
* Bearer tokens can be generated from your Bitquery ID account.
* A code generator is available in the Bitquery IDE for multiple programming languages.

## Setting Up Claude Configuration

* Go to Claude settings and open the **Developer** section.
* Link your Python library and specify the MCP code location in the Claude desktop configuration file.

## Interacting with the MCP via Claude

* Open a new chat in Claude and use a slash command followed by the function name (for example, `/get_trending_tokens`) to retrieve data from the MCP.
* You can build custom functions that combine multiple data points and ask Claude questions to support buy/sell decision-making.

## Conclusion

* You can build an MCP for DEX trading and interact with it using Bitquery data.
* Support is available for follow-up questions or further customization.
