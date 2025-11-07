"""
Script to email the Bitcoin analysis report
"""

import os
import smtplib
import re
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def extract_text_from_html(html_file):
    """Extract and clean text content from HTML file"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def format_professional_report(raw_text):
    """Format the extracted text in a professional Wall Street trader tone"""
    
    # Remove emojis and Gen Z slang, make it professional
    text = raw_text
    
    # Replace common Gen Z phrases with professional equivalents
    replacements = {
        'no cap': '',
        'periodt': '',
        'vibe check': 'Market Assessment',
        'bestie': '',
        'lowkey': '',
        'highkey': '',
        'fr fr': '',
        'that\'s facts': '',
        'stay woke': '',
        'it\'s giving': 'indicating',
        'slay': 'perform well',
        'fire': 'strong',
        'lit': 'active',
        'tea': 'information',
        'spill the tea': 'provide details',
    }
    
    for slang, professional in replacements.items():
        text = re.sub(rf'\b{re.escape(slang)}\b', professional, text, flags=re.IGNORECASE)
    
    # Remove emojis
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    
    # Format as professional report
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Capitalize section headers
        if line.isupper() or (len(line) < 50 and ':' in line):
            formatted_lines.append(f"\n{line.upper()}\n{'=' * len(line)}\n")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def send_bitcoin_report():
    """Send the Bitcoin analysis report via email"""
    
    # Get credentials from .env
    gmail_email = os.getenv('GMAIL_EMAIL')
    gmail_password = os.getenv('GMAIL_PASSWORD')
    recipient_email = 'candice.shen@yale.edu'
    
    if not gmail_email or not gmail_password:
        print("❌ Gmail credentials not found in .env file")
        return False
    
    # Check if output.html exists
    html_file = 'output.html'
    if not os.path.exists(html_file):
        print(f"❌ {html_file} not found!")
        return False
    
    try:
        # Extract and format text from HTML
        print("📄 Extracting content from HTML...")
        raw_text = extract_text_from_html(html_file)
        
        if not raw_text:
            print("❌ Failed to extract text from HTML")
            return False
        
        # Format professionally
        professional_report = format_professional_report(raw_text)
        
        # Create professional email body
        body = f"""BITCOIN MARKET ANALYSIS REPORT
{'-' * 50}

Dear Candice,

Please find below our comprehensive Bitcoin market analysis and trading recommendations based on recent market data and sentiment analysis.

{professional_report}

{'-' * 50}

TRADING RECOMMENDATION SUMMARY

Based on our analysis of current market conditions, technical indicators, and fundamental factors, we provide the following actionable insights for your consideration.

Please note: This analysis is for informational purposes only and should not be considered as financial advice. Always conduct your own due diligence and consult with a qualified financial advisor before making trading decisions.

Best regards,
Bitcoin Analysis System

---
This report was generated automatically based on real-time market data and sentiment analysis.
"""
        
        # Create message
        msg = MIMEText(body, 'plain')
        msg['From'] = gmail_email
        msg['To'] = recipient_email
        msg['Subject'] = 'Bitcoin Trading Analysis Report - Market Intelligence'
        
        # Send email
        print(f"📧 Sending email to {recipient_email}...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_email, gmail_password)
        server.sendmail(gmail_email, recipient_email, msg.as_string())
        server.quit()
        
        print(f"✅ Email sent successfully to {recipient_email}!")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    send_bitcoin_report()

