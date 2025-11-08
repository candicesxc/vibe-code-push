"""
Bitcoin Trading Analysis System using CrewAI
Analyzes recent Bitcoin articles and provides buy/sell recommendations
"""

import sys
import os
import json
import base64
from datetime import date
from pathlib import Path

from openai import OpenAI

# Check Python version
MIN_PYTHON_VERSION = (3, 8)
if sys.version_info < MIN_PYTHON_VERSION:
    print(f"\n❌ Python version error!")
    print(f"   This script requires Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} or higher.")
    print(f"   Your current version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"\n💡 To fix this:")
    print(f"   1. Install Python 3.8+ from https://www.python.org/downloads/")
    print(f"   2. Or use pyenv: pyenv install 3.11")
    print(f"   3. Or use conda: conda create -n bitcoin python=3.11")
    sys.exit(1)

# Try to import required packages with helpful error messages
try:
    from dotenv import load_dotenv
except ImportError:
    print("\n❌ Missing package: python-dotenv")
    print("   Install it with: pip install python-dotenv")
    sys.exit(1)

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import tool
except ImportError as e:
    print("\n❌ Missing package: crewai")
    print("   Install it with: pip install crewai")
    print(f"   Error details: {e}")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Create custom tools using the tool decorator
@tool("Search the web for recent articles")
def search_web_tool(query: str) -> str:
    """Search the web for recent articles using SerpAPI.
    
    Args:
        query: The search query string
        
    Returns:
        Search results as a string
    """
    try:
        import requests
        serpapi_key = os.getenv('SERPER_API_KEY')  # Using SERPER_API_KEY env var name for SerpAPI key
        if not serpapi_key or serpapi_key in ['your_serper_api_key_here', '']:
            return "Error: SERPER_API_KEY not set in .env file"
        
        # Use SerpAPI endpoint (serpapi.com)
        url = "https://serpapi.com/search.json"
        params = {
            'q': query,
            'api_key': serpapi_key,
            'num': 10,
            'engine': 'google'
        }
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = []
            # SerpAPI uses 'organic_results' instead of 'organic'
            if 'organic_results' in data:
                for item in data['organic_results']:
                    title = item.get('title', 'N/A')
                    link = item.get('link', 'N/A')
                    snippet = item.get('snippet', item.get('about_this_result', {}).get('source', {}).get('description', 'N/A'))
                    results.append(f"Title: {title}\nURL: {link}\nSnippet: {snippet}\n")
            return "\n".join(results) if results else "No results found"
        elif response.status_code == 401 or response.status_code == 403:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('error', 'Unauthorized')
            return f"Error: SerpAPI authentication failed ({response.status_code}). Please check your SERPER_API_KEY in .env file. The key may be invalid, expired, or your account may have exceeded its quota. Visit https://serpapi.com to verify your API key. Error: {error_msg}"
        elif response.status_code == 429:
            return f"Error: SerpAPI rate limit exceeded (429). Please wait a moment and try again, or check your quota at https://serpapi.com"
        else:
            error_detail = response.text[:200] if response.text else 'No details'
            return f"Error: SerpAPI returned status code {response.status_code}. Details: {error_detail}"
    except Exception as e:
        return f"Error searching: {str(e)}"

@tool("Read content from a website URL")
def read_website_tool(url: str) -> str:
    """Read and extract content from a website URL.
    
    Args:
        url: The website URL to read
        
    Returns:
        Website content as a string
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:5000] if len(text) > 5000 else text  # Limit to 5000 chars
    except Exception as e:
        return f"Error reading website: {str(e)}"

# Initialize tools
search_tool = search_web_tool
website_tool = read_website_tool

def _fallback_persona() -> dict:
    return {
        "name": "Aurora Theta",
        "title": "AI Market Strategist",
        "bio": ("Aurora Theta examines digital asset flows and macro signals to place each day's bitcoin movements "
                "in institutional context."),
        "image_src": "https://via.placeholder.com/160?text=AI"
    }


def generate_fake_investor() -> dict:
    """Return (and cache) a fictional AI investor persona for today's date."""
    today = date.today().isoformat()
    cache_path = Path("persona_cache.json")
    images_dir = Path("images")
    images_dir.mkdir(parents=True, exist_ok=True)

    cache: dict = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}

    cached = cache.get(today)
    if cached:
        image_src = cached.get("image_src")
        if image_src and (image_src.startswith("http") or Path(image_src).exists()):
            return cached

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_persona()

    client = OpenAI()

    persona_prompt = (
        "You are creating a fictional AI investor persona for a professional bitcoin market report. "
        f"Seed the persona with today's date ({today}) so the persona is stable for the day. "
        "Return STRICT JSON with keys name, title, bio. "
        "The bio must be 1-2 sentences, written in a serious financial-press tone. "
        "Example:\n"
        "{\"name\": \"...\", \"title\": \"...\", \"bio\": \"...\"}"
    )

    try:
        chat_response = client.chat.completions.create(
            model=os.getenv("OPENAI_PERSONA_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            messages=[
                {"role": "system", "content": "You generate concise professional personas."},
                {"role": "user", "content": persona_prompt}
            ]
        )
        content = chat_response.choices[0].message.content.strip()
        json_start = content.find("{")
        json_end = content.rfind("}")
        persona_data = _fallback_persona()
        if json_start != -1 and json_end != -1:
            persona_data = json.loads(content[json_start:json_end + 1])
        persona = {
            "name": persona_data.get("name", _fallback_persona()["name"]),
            "title": persona_data.get("title", _fallback_persona()["title"]),
            "bio": persona_data.get("bio", _fallback_persona()["bio"]),
            "image_src": _fallback_persona()["image_src"]
        }
    except Exception:
        return _fallback_persona()

    image_prompt = (
        f"Formal headshot photograph of {persona['name']}, {persona['title']}, financial analyst, "
        "neutral studio lighting, looking at the camera, for use in a newspaper profile, no text, no logo."
    )

    try:
        image_response = client.images.generate(
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            prompt=image_prompt,
            size="512x512"
        )
        image_data = image_response.data[0].b64_json
        if image_data:
            image_bytes = base64.b64decode(image_data)
            safe_name = persona["name"].lower().replace(" ", "_").replace(".", "")
            image_path = images_dir / f"{safe_name}_{today.replace('-', '')}.png"
            with image_path.open("wb") as f:
                f.write(image_bytes)
            persona["image_src"] = image_path.as_posix()
    except Exception:
        # Keep fallback image_src
        pass

    cache[today] = persona
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    return persona


class BitcoinAnalyzer:
    def __init__(self):
        self.setup_agents()
        self.setup_tasks()
        self.setup_crew()
    
    def setup_agents(self):
        """Initialize all CrewAI agents"""
        
        # Google Search Agent
        self.search_agent = Agent(
            role='Bitcoin News Researcher',
            goal='Find the most recent and relevant Bitcoin articles from the past 24 hours',
            backstory="""You are an expert researcher specializing in cryptocurrency news.
            You excel at finding the latest, most relevant articles about Bitcoin from
            reputable sources. You focus on recent news that could impact trading decisions.""",
            tools=[search_tool],
            verbose=True,
            allow_delegation=False
        )
        
        # Article Reader Agent
        self.reader_agent = Agent(
            role='Article Analyst',
            goal='Extract and summarize key information from Bitcoin articles',
            backstory="""You are a skilled financial journalist with deep understanding
            of cryptocurrency markets. You can quickly identify the most important
            information in articles, including price movements, market sentiment,
            technical analysis, and major news events.""",
            tools=[website_tool],
            verbose=True,
            allow_delegation=False
        )
        
        # Synthesis Agent
        self.synthesis_agent = Agent(
            role='Market Intelligence Synthesizer',
            goal='Combine multiple article summaries into coherent market insights',
            backstory="""You are a senior market analyst who excels at identifying patterns
            and trends across multiple sources. You can synthesize information from various
            articles to create a comprehensive view of the current Bitcoin market situation.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Analyst Agent
        self.analyst_agent = Agent(
            role='Trading Strategist',
            goal='Provide clear buy/sell/hold recommendations based on market analysis',
            backstory="""You are an experienced cryptocurrency trading strategist with
            a track record of successful market predictions. You analyze market data,
            sentiment, and trends to provide actionable trading recommendations.
            You are conservative and base recommendations on solid evidence.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Website Agent
        self.website_agent = Agent(
            role='Financial News Layout Editor',
            goal='Prepare clear sectioned HTML content for a professional financial article in the tone of major newspapers such as The New York Times.',
            backstory="""You are a meticulous financial news layout editor. You produce semantic, well-structured HTML
            containing only the essential sections of the Bitcoin report (Articles Found, Article Analysis & Summaries,
            Market Synthesis, Final Trading Recommendation). Avoid decorative styling, animations, or bright colors.
            Focus on clean markup (headings, paragraphs, lists) with informative text that can be restyled later.""",
            verbose=True,
            allow_delegation=False
        )
    
    def setup_tasks(self):
        """Define tasks for each agent"""
        
        # Task 1: Search for recent articles
        self.search_task = Task(
            description="""Search for the most recent Bitcoin articles from the past 24 hours.
            Focus on articles from reputable financial news sources, cryptocurrency news sites,
            and major news outlets. Retrieve up to 10 of the most relevant articles.
            Include article titles, URLs, and brief descriptions.""",
            agent=self.search_agent,
            expected_output="""A list of recent Bitcoin articles with:
            - Article titles
            - Source URLs
            - Brief descriptions
            - Publication dates (if available)"""
        )
        
        # Task 2: Read and summarize articles
        self.reader_task = Task(
            description="""Using the articles found by the search agent, read each article
            and extract and summarize:
            1. Main topic and key points
            2. Price movements mentioned
            3. Market sentiment (bullish/bearish/neutral)
            4. Technical indicators or analysis
            5. Major news events or catalysts
            6. Risk factors mentioned
            
            Create concise summaries (2-3 sentences per article) highlighting
            the most important trading-relevant information. Use the website tool
            to fetch the full content of each article URL.""",
            agent=self.reader_agent,
            context=[self.search_task],
            expected_output="""A structured summary for each article containing:
            - Key points
            - Market sentiment
            - Price implications
            - Risk factors"""
        )
        
        # Task 3: Synthesize information
        self.synthesis_task = Task(
            description="""Using the article summaries from the reader agent, combine all
            summaries into a comprehensive market analysis. Identify:
            1. Common themes and patterns across articles
            2. Overall market sentiment (bullish/bearish/neutral)
            3. Key price levels or trends mentioned
            4. Major catalysts or events
            5. Conflicting information or uncertainties
            6. Consensus views vs. outlier opinions
            
            Create a unified view of the current Bitcoin market situation.""",
            agent=self.synthesis_agent,
            context=[self.reader_task],
            expected_output="""A comprehensive synthesis report with:
            - Overall market sentiment
            - Key themes and patterns
            - Price trends and levels
            - Major catalysts
            - Risk assessment"""
        )
        
        # Task 4: Provide trading recommendation
        self.analyst_task = Task(
            description="""Based on the synthesized market analysis from the synthesis agent,
            provide a clear trading recommendation for TODAY:
            
            1. Recommendation: BUY, SELL, or HOLD
            2. Confidence level: High, Medium, or Low
            3. Key reasons supporting the recommendation
            4. Risk factors to consider
            5. Suggested entry/exit points (if applicable)
            6. Time horizon for the recommendation
            
            Be specific and actionable. Base your recommendation on the evidence
            from the articles analyzed.""",
            agent=self.analyst_agent,
            context=[self.synthesis_task],
            expected_output="""A clear trading recommendation with:
            - BUY/SELL/HOLD decision
            - Confidence level
            - Supporting reasons
            - Risk factors
            - Entry/exit guidance"""
        )
        
        # Task 5: Create structured HTML content for the report
        self.website_task = Task(
            description="""Produce clean, semantic HTML content (without inline styling) that contains the latest Bitcoin
            report in clearly marked sections with the following IDs:
            - #articles-found : includes an <h2> and an unordered list (<ul id="articles-list">) of up to 10 articles with anchors.
            - #article-analysis : includes an <h2> and a series of <article> elements summarizing each article.
            - #market-synthesis : includes an <h2> and several <p> elements summarising market synthesis points.
            - #final-recommendation : includes an <h2>, paragraphs, and bullet lists describing recommendation, confidence,
              reasons, risk factors, and suggested entry/exit points.
            Keep the tone professional and data-driven. Avoid decorative language and do not include CSS or JavaScript.
            The HTML will be restyled later, so focus on structure and clarity only.""",
            agent=self.website_agent,
            context=[self.search_task, self.reader_task, self.synthesis_task, self.analyst_task],
            expected_output="""Semantic HTML fragment with sections #articles-found, #article-analysis, #market-synthesis,
            and #final-recommendation, each containing descriptive headings, paragraphs, and lists with up-to-date analysis."""
        )
    
    def setup_crew(self):
        """Create the Crew with all agents and tasks"""
        self.crew = Crew(
            agents=[
                self.search_agent,
                self.reader_agent,
                self.synthesis_agent,
                self.analyst_agent,
                self.website_agent
            ],
            tasks=[
                self.search_task,
                self.reader_task,
                self.synthesis_task,
                self.analyst_task,
                self.website_task
            ],
            process=Process.sequential,
            verbose=True
        )
    
    def analyze(self, topic="Bitcoin market today"):
        """Run the analysis pipeline"""
        print(f"\n🔍 Starting analysis for: {topic}\n")
        print("=" * 60)
        
        # Update search task with the topic
        self.search_task.description = f"""Search for the most recent articles about: {topic}
        Focus on articles from the past 24 hours. Retrieve up to 10 of the most relevant articles
        from reputable financial news sources, cryptocurrency news sites, and major news outlets.
        Include article titles, URLs, and brief descriptions."""
        
        # Execute the crew
        persona = generate_fake_investor()
        result = self.crew.kickoff()
        
        # Extract HTML from the result and save it
        self._save_html_output(result, persona)
        
        return result
    
    def _save_html_output(self, result, persona):
        """Extract and save HTML output from the website agent"""
        try:
            # Get the output from the website task
            # CrewAI returns the last task's output as the main result
            website_output = str(result)
            
            # Try to extract HTML content if it's wrapped in markdown code blocks
            html_content = None
            
            # Check for HTML in markdown code blocks
            if "```html" in website_output:
                html_content = website_output.split("```html")[1].split("```")[0].strip()
            elif "```" in website_output:
                # Try to find HTML between code blocks
                parts = website_output.split("```")
                for part in parts:
                    if "<html" in part.lower() or "<!doctype" in part.lower() or "<body" in part.lower():
                        html_content = part.strip()
                        break
                if not html_content:
                    # Check if any part looks like HTML
                    for part in parts:
                        if part.strip().startswith("<") and len(part.strip()) > 100:
                            html_content = part.strip()
                            break
            
            # If no HTML found in code blocks, use the full output
            if not html_content:
                html_content = website_output.strip()
            
            # Clean up any markdown formatting
            html_content = html_content.replace("```html", "").replace("```", "").strip()
            
            # Ensure it's valid HTML (wrap if necessary)
            if not html_content.strip().startswith("<!DOCTYPE") and not html_content.strip().startswith("<html"):
                html_content = f"<!DOCTYPE html><html><body>{html_content}</body></html>"

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            def extract_articles() -> list:
                items = []
                article_list = soup.find(id="articles-list")
                if article_list:
                    for li in article_list.find_all("li"):
                        link = li.find("a")
                        title = link.get_text(strip=True) if link else li.get_text(strip=True)
                        href = link.get("href") if link else None
                        if title:
                            items.append({"title": title, "href": href})
                return items

            def extract_analysis() -> list:
                entries = []
                section = soup.find(id="article-analysis")
                if section:
                    for block in section.find_all(["article", "p"]):
                        text = block.get_text(" ", strip=True)
                        if text:
                            entries.append(text)
                return entries

            def extract_synthesis() -> list:
                paragraphs = []
                section = soup.find(id="market-synthesis")
                if section:
                    for p_tag in section.find_all("p"):
                        text = p_tag.get_text(" ", strip=True)
                        if text:
                            paragraphs.append(text)
                return paragraphs

            def extract_recommendation() -> dict:
                result_data = {"paragraphs": [], "lists": []}
                section = soup.find(id="final-recommendation")
                if not section:
                    return result_data
                for child in section.find_all(["p", "ul", "ol"], recursive=False):
                    if child.name == "p":
                        text = child.get_text(" ", strip=True)
                        if text:
                            result_data["paragraphs"].append(text)
                    elif child.name in ("ul", "ol"):
                        items = [li.get_text(" ", strip=True) for li in child.find_all("li")]
                        if items:
                            result_data["lists"].append(items)
                return result_data

            articles = extract_articles()
            analysis = extract_analysis()
            synthesis = extract_synthesis()
            recommendation = extract_recommendation()

            article_items_html = "\n".join(
                f'<li><a href="{item["href"]}" target="_blank" rel="noopener noreferrer">{item["title"]}</a></li>'
                if item["href"] else f'<li>{item["title"]}</li>'
                for item in articles
            ) or '<li>No recent articles were retrieved.</li>'

            analysis_html = "\n".join(
                f'<article class="analysis-entry"><p>{text}</p></article>' for text in analysis
            ) or '<p class="empty-state">Analysis summaries are not available.</p>'

            synthesis_html = "\n".join(
                f'<p>{paragraph}</p>' for paragraph in synthesis
            ) or '<p class="empty-state">Market synthesis is not available.</p>'

            recommendation_paragraphs = "\n".join(
                f'<p>{para}</p>' for para in recommendation["paragraphs"]
            )
            recommendation_lists = "\n".join(
                "<ul>" + "".join(f"<li>{item}</li>" for item in lst) + "</ul>"
                for lst in recommendation["lists"]
            )
            if not recommendation_paragraphs and not recommendation_lists:
                recommendation_block = '<p class="empty-state">No trading recommendation supplied.</p>'
            else:
                recommendation_block = recommendation_paragraphs + recommendation_lists

            persona_note = (
                f"Daily commentary by {persona['name']}, AI-generated fictional market analyst."
            )
            persona_image_src = persona.get("image_src") or _fallback_persona()["image_src"]

            html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bitcoin Market Analysis Report</title>
  <style>
    :root {{
      color-scheme: light;
    }}
    body {{
      margin: 0;
      font-family: "Georgia", "Times New Roman", serif;
      background-color: #f8f7f5;
      color: #111111;
    }}
    a {{
      color: #0b63ce;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .page {{
      max-width: 760px;
      margin: 0 auto;
      padding: 3rem 1.5rem 4rem;
      background-color: #ffffff;
      min-height: 100vh;
    }}
    header.masthead {{
      border-bottom: 1px solid #e0e0e0;
      padding-bottom: 1.75rem;
      margin-bottom: 1.75rem;
    }}
    header.masthead h1 {{
      font-size: 2.4rem;
      line-height: 1.2;
      margin: 0 0 0.75rem 0;
      font-weight: 700;
      color: #111111;
    }}
    header.masthead p.subheading {{
      font-size: 1.1rem;
      line-height: 1.6;
      color: #4a4a4a;
      margin: 0;
    }}
    .persona-block {{
      display: flex;
      gap: 1.5rem;
      border-bottom: 1px solid #e0e0e0;
      padding-bottom: 1.75rem;
      margin-bottom: 2rem;
      align-items: center;
    }}
    .persona-block img {{
      width: 108px;
      height: 108px;
      object-fit: cover;
      border-radius: 50%;
      background-color: #ddd;
      flex-shrink: 0;
    }}
    .persona-details {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}
    .persona-name {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #111111;
    }}
    .persona-title {{
      font-size: 1.05rem;
      color: #333333;
    }}
    .persona-bio {{
      font-size: 1rem;
      line-height: 1.6;
      color: #444444;
    }}
    .persona-note {{
      font-size: 0.95rem;
      color: #666666;
    }}
    main {{
      line-height: 1.65;
    }}
    section {{
      margin-bottom: 2.5rem;
    }}
    section h2 {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #333333;
      border-bottom: 1px solid #e0e0e0;
      padding-bottom: 0.75rem;
      margin-bottom: 1.25rem;
    }}
    .article-list {{
      list-style: disc;
      padding-left: 1.4rem;
      margin: 0;
    }}
    .article-list li {{
      margin-bottom: 0.65rem;
      font-size: 1rem;
    }}
    .article-list li:hover {{
      background-color: #f3f3f3;
    }}
    .article-list li a {{
      display: inline-block;
      padding: 0.2rem 0;
    }}
    .analysis-entry {{
      margin-bottom: 1.35rem;
    }}
    .analysis-entry p {{
      margin: 0;
      font-size: 1rem;
    }}
    #market-synthesis p {{
      margin: 0 0 1rem 0;
      font-size: 1rem;
    }}
    .recommendation-box {{
      background-color: #fafafa;
      border: 1px solid #e0e0e0;
      padding: 1.5rem;
      font-size: 1rem;
    }}
    .recommendation-box ul {{
      list-style: disc;
      margin: 0 0 1rem 1.4rem;
      padding: 0;
    }}
    .recommendation-box li {{
      margin-bottom: 0.5rem;
    }}
    .email-signup {{
      border-top: 1px solid #e0e0e0;
      border-bottom: 1px solid #e0e0e0;
      padding: 1.75rem 0;
    }}
    .email-signup h3 {{
      font-size: 1.3rem;
      margin-top: 0;
      margin-bottom: 0.75rem;
      color: #333333;
    }}
    .email-form {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .email-form input[type="email"] {{
      flex: 1 1 280px;
      padding: 0.65rem 0.85rem;
      border: 1px solid #c8c8c8;
      border-radius: 4px;
      font-size: 1rem;
      font-family: "Georgia", "Times New Roman", serif;
      color: #111111;
      background-color: #ffffff;
    }}
    .email-form input[type="email"]:focus {{
      outline: 2px solid #0b63ce;
      outline-offset: 2px;
    }}
    .email-form button {{
      padding: 0.65rem 1.4rem;
      border: 1px solid #0b63ce;
      background-color: #0b63ce;
      color: #ffffff;
      font-size: 1rem;
      font-family: "Georgia", "Times New Roman", serif;
      border-radius: 4px;
      cursor: pointer;
    }}
    .email-form button:disabled {{
      background-color: #9fbce0;
      border-color: #9fbce0;
      cursor: not-allowed;
    }}
    #email-message {{
      margin-top: 0.75rem;
      font-size: 0.95rem;
      color: #333333;
    }}
    footer.disclaimer {{
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 1px solid #e0e0e0;
      font-size: 0.95rem;
      color: #555555;
      line-height: 1.6;
    }}
    @media (max-width: 640px) {{
      .persona-block {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .persona-block img {{
        width: 88px;
        height: 88px;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="masthead">
      <h1>Bitcoin Market Analysis Report</h1>
      <p class="subheading">Daily analysis of bitcoin price action, market flows, and key risks.</p>
    </header>

    <section class="persona-block" aria-label="AI Analyst Persona">
      <img src="{persona_image_src}" alt="{persona['name']} headshot portrait" />
      <div class="persona-details">
        <p class="persona-name">{persona['name']}</p>
        <p class="persona-title">{persona['title']}</p>
        <p class="persona-bio">{persona['bio']}</p>
        <p class="persona-note">{persona_note}</p>
      </div>
    </section>

    <main>
      <section id="articles-found" aria-label="Articles Found" tabindex="0">
        <h2>Articles Found</h2>
        <ul class="article-list">
          {article_items_html}
        </ul>
      </section>

      <section id="article-analysis" aria-label="Article Analysis and Summaries" tabindex="0">
        <h2>Article Analysis &amp; Summaries</h2>
        {analysis_html}
      </section>

      <section id="market-synthesis" aria-label="Complete Market Synthesis Report" tabindex="0">
        <h2>Market Synthesis</h2>
        {synthesis_html}
      </section>

      <section id="final-recommendation" aria-label="Final Trading Recommendation" tabindex="0">
        <h2>Final Trading Recommendation</h2>
        <div class="recommendation-box">
          {recommendation_block}
        </div>
      </section>

      <section class="email-signup" id="email-section" aria-label="Email Report Section">
        <h3>Receive the Report</h3>
        <p>Enter your email address to have the daily summary delivered to your inbox.</p>
        <div class="email-form">
          <input aria-describedby="email-message" aria-required="true" autocomplete="email" id="user-email" placeholder="Enter your email address" required type="email" />
          <button aria-busy="false" aria-live="polite" id="send-report-btn" onclick="sendReport()" disabled>Send Report</button>
        </div>
        <div aria-live="assertive" id="email-message" role="alert"></div>
      </section>
    </main>

    <footer class="disclaimer">
      <p>This report and analyst persona are AI generated for informational and educational purposes only and do not constitute financial advice. Always perform independent research or consult a licensed financial professional before making investment decisions.</p>
    </footer>
  </div>

  <script>
    function updateReportDate() {{
      const dateElem = document.getElementById('report-date');
      if (!dateElem) return;
      const now = new Date();
      const options = {{ year: 'numeric', month: 'long', day: 'numeric' }};
      const formattedDate = now.toLocaleDateString('en-US', options);
      dateElem.textContent = 'Report Date: ' + formattedDate;
    }}
    updateReportDate();

    const emailInput = document.getElementById('user-email');
    const sendBtn = document.getElementById('send-report-btn');
    const emailMsg = document.getElementById('email-message');

    function validateEmail(email) {{
      const re = /^[a-zA-Z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{{2,}}$/i;
      return re.test(String(email).toLowerCase());
    }}

    window.sendReport = async function() {{
      const email = emailInput.value.trim();
      if (!validateEmail(email)) {{
        emailMsg.textContent = 'Please enter a valid email address!';
        emailMsg.style.color = '#b70000';
        return;
      }}

      sendBtn.disabled = true;
      sendBtn.textContent = 'Sending...';
      emailMsg.textContent = 'Sending report...';
      emailMsg.style.color = '#0f3c73';

      try {{
        const response = await fetch('http://localhost:5050/send-report', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
          }},
          body: JSON.stringify({{ email }})
        }});
        const data = await response.json();
        if (data.success) {{
          emailMsg.textContent = 'Report sent successfully!';
          emailMsg.style.color = '#146414';
          emailInput.value = '';
        }} else {{
          emailMsg.textContent = 'Error: ' + (data.error || 'Failed to send report');
          emailMsg.style.color = '#b70000';
        }}
      }} catch (error) {{
        emailMsg.textContent = 'Error: Could not connect to server. Make sure the email API is running.';
        emailMsg.style.color = '#b70000';
      }} finally {{
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send Report';
      }}
    }};

    emailInput.addEventListener('input', () => {{
      const isValid = validateEmail(emailInput.value.trim());
      sendBtn.disabled = !isValid;
      if (!isValid && emailInput.value.trim().length > 0) {{
        emailMsg.textContent = 'Please enter a valid email address!';
        emailMsg.style.color = '#b70000';
      }} else {{
        emailMsg.textContent = '';
      }}
    }});

    window.addEventListener('load', () => {{
      emailInput.focus();
    }});
  </script>
</body>
</html>
"""

            output_path = os.path.join(os.getcwd(), "index.html")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_output)
            
            print(f"\n✨ HTML report saved to: {output_path}")
            print("   Email API reminder: EMAIL_API_PORT=5050 python3.11 email_api.py")
            
        except Exception as e:
            print(f"\n⚠️  Warning: Could not save HTML output: {e}")
            print("The analysis completed successfully, but HTML generation had an issue.")
            import traceback
            traceback.print_exc()


def check_environment():
    """Check if the environment is properly set up"""
    issues = []
    
    # Check Python version (already checked at import, but double-check)
    if sys.version_info < MIN_PYTHON_VERSION:
        issues.append(f"Python version {sys.version_info.major}.{sys.version_info.minor} is too old (need {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+)")
    
    # Check for required API keys
    required_keys = ['OPENAI_API_KEY', 'SERPER_API_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key) or os.getenv(key).strip() in ['', 'your_openai_api_key_here', 'your_serper_api_key_here']]
    
    if missing_keys:
        issues.append(f"Missing API keys: {', '.join(missing_keys)}")
    
    return len(issues) == 0, issues


def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("🚀 Bitcoin Trading Analysis System")
    print("=" * 60)
    
    # Check environment
    env_ok, issues = check_environment()
    
    if not env_ok:
        print("\n❌ Environment check failed!")
        for issue in issues:
            print(f"   - {issue}")
        
        # Provide helpful guidance
        if any("API keys" in issue for issue in issues):
            print("\n💡 To fix API keys:")
            print("   1. Edit your .env file")
            print("   2. Get OpenAI API key: https://platform.openai.com/api-keys")
            print("   3. Get Serper API key: https://serper.dev (free tier available)")
        
        if any("Python version" in issue for issue in issues):
            print("\n💡 To fix Python version:")
            print("   1. Install Python 3.8+ from https://www.python.org/downloads/")
            print("   2. Or use pyenv: pyenv install 3.11")
            print("   3. Or use conda: conda create -n bitcoin python=3.11")
        
        print("\n")
        return
    
    # Initialize analyzer
    analyzer = BitcoinAnalyzer()
    
    # Run analysis
    topic = "Bitcoin market today trading analysis"
    result = analyzer.analyze(topic)
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 ANALYSIS COMPLETE")
    print("=" * 60)
    print("\n" + str(result))
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

