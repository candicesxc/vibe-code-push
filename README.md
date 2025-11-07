# Bitcoin Trading Analysis System

An automated AI-powered system that analyzes recent Bitcoin articles and provides daily trading recommendations (BUY/SELL/HOLD) using CrewAI and OpenAI GPT-4o.

## Features

- 🔍 **Automated News Search**: Uses SerpAPI to find the most recent Bitcoin articles (past 24 hours)
- 📖 **Article Analysis**: Extracts and summarizes key information from articles
- 🧠 **Market Synthesis**: Combines multiple sources into coherent market insights
- 💡 **Trading Recommendations**: Provides actionable BUY/SELL/HOLD recommendations with confidence levels

## Architecture

The system uses a 4-agent CrewAI workflow:

1. **Google Search Agent**: Searches for recent Bitcoin articles using SerpAPI
2. **Article Reader Agent**: Extracts and summarizes key information from articles
3. **Synthesis Agent**: Combines all summaries into a unified market analysis
4. **Analyst Agent**: Provides trading recommendations based on the analysis

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit the `.env` file and add your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

**Getting API Keys:**
- **OpenAI**: Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Serper API**: Get your API key from [Serper.dev](https://serper.dev) (free tier available)

### 3. Run the Analysis

```bash
python bitcoin_analyzer.py
```

## Output

The system provides:
- List of recent articles analyzed
- Summarized key points from each article
- Synthesized market analysis
- **Trading Recommendation**: BUY/SELL/HOLD with:
  - Confidence level (High/Medium/Low)
  - Supporting reasons
  - Risk factors
  - Entry/exit guidance

## Example Usage

```python
from bitcoin_analyzer import BitcoinAnalyzer

analyzer = BitcoinAnalyzer()
result = analyzer.analyze("Bitcoin market today trading analysis")
print(result)
```

## Requirements

- Python 3.8+
- OpenAI API key (for GPT-4o)
- Serper API key (for Google search)

## Notes

- The system analyzes articles from the past 24 hours
- Recommendations are based on recent news and market sentiment
- Always do your own research before making trading decisions
- This tool is for informational purposes only, not financial advice

## License

MIT

