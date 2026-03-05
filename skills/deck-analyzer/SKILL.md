---
name: deck-analyzer
description: "[DEPRECATED] Use deal-analyzer instead. Extract structured information from pitch decks."
version: 1.0.0
author: GroundUp VC
actions:
  - analyze
  - extract-links
  - test
---

# Deck Analyzer Skill [DEPRECATED]

> **This skill is deprecated.** Use `deal-analyzer` instead, which includes all deck extraction capabilities plus web research, 12-section analysis, retry logic, and full HubSpot integration.

AI-powered pitch deck analysis that extracts structured company information from various deck sources.

## When to Use This Skill

Use this skill when you need to:
- **Analyze a pitch deck** from a URL or text
- **Extract company information** (name, product, team, traction)
- **Prepare HubSpot descriptions** from deck content
- **Quick deck review** without manual reading
- **Find deck links** in email text or messages

Natural language triggers:
- "analyze this deck: [URL]"
- "extract info from this pitch deck"
- "what's in this deck?"
- "review this pitch deck"
- "get company info from deck"

## Features

- 🔗 **Multi-source support** - DocSend, Google Drive, Dropbox, PDF links
- 🤖 **AI-powered extraction** - Uses Claude to understand deck content
- 📊 **Structured output** - Company, product, team, GTM, traction, fundraising
- 💼 **HubSpot-ready** - Formats descriptions for CRM entry
- 🔍 **Link detection** - Automatically finds deck links in text

## Actions

### analyze

Analyze a pitch deck from a URL and extract structured information.

**Usage:**
```bash
deck-analyzer analyze <DECK_URL> [SENDER_EMAIL]
```

**Arguments:**
- `DECK_URL` - Link to the pitch deck (DocSend, Google Drive, Dropbox, PDF)
- `SENDER_EMAIL` - (Optional) Email of sender for DocSend authentication

**Example:**
```bash
deck-analyzer analyze https://docsend.com/view/abc123xyz
deck-analyzer analyze https://docs.google.com/presentation/d/1abc/edit
```

**Output:**
```json
{
  "company_name": "Acme Corp",
  "product_overview": "AI-powered workflow automation platform",
  "problem_solution": "Companies waste 40% time on manual tasks...",
  "key_capabilities": "Natural language automation, integration hub...",
  "team_background": "CEO: ex-Google AI, CTO: ex-Microsoft Azure...",
  "gtm_strategy": "Enterprise B2B, starting with Fortune 500...",
  "traction": "3 pilot customers, $50K ARR...",
  "fundraising": "Raising $2M seed round"
}
```

**HubSpot-formatted description also provided**

### extract-links

Extract all deck links from text (email body, message, etc.).

**Usage:**
```bash
deck-analyzer extract-links <TEXT_FILE>
# Or via stdin:
echo "Check out our deck: https://docsend.com/view/abc123" | deck-analyzer extract-links
```

**Supported formats:**
- DocSend: `https://docsend.com/view/...`
- Google Docs: `https://docs.google.com/...`
- Google Drive: `https://drive.google.com/...`
- Dropbox: `https://www.dropbox.com/...`
- PDF files: `https://*/**.pdf`

### test

Run a test analysis with sample deck content.

**Usage:**
```bash
deck-analyzer test
```

Tests the analyzer with a built-in sample deck to verify configuration.

## Extracted Information

The analyzer extracts these fields:

1. **Company Name** - Company or startup name
2. **Product Overview** - 1-2 sentence summary of the product
3. **Problem/Solution** - Problem being solved and the solution
4. **Key Capabilities** - Main features or differentiators
5. **Team Background** - Founders and key team members
6. **GTM Strategy** - Go-to-market approach and target customers
7. **Traction/Validation** - Current traction, customers, metrics
8. **Fundraising Ask** - Funding amount and use of funds

If a field is not mentioned in the deck, it's omitted from output.

## Environment Requirements

**Required:**
- `ANTHROPIC_API_KEY` - Claude API key for deck analysis

**Optional:**
- Sender email for DocSend authentication

## Integration Examples

### From OpenClaw Agent

```bash
openclaw agent ask "Analyze this deck: https://docsend.com/view/abc123"
```

The agent will automatically use this skill to fetch and analyze the deck.

### From Deal Logger

The deal-logger skill can automatically use deck-analyzer when it finds deck links in emails:

```python
# In deal logging workflow
deck_links = extract_deck_links(email_body)
if deck_links:
    deck_info = analyze_deck(deck_links[0], sender_email)
    # Use deck_info to enrich deal description
```

### Manual CLI

```bash
# Analyze a specific deck
~/.openclaw/skills/deck-analyzer/deck-analyzer analyze https://docsend.com/view/abc123

# Extract links from an email
cat email.txt | ~/.openclaw/skills/deck-analyzer/deck-analyzer extract-links

# Test the analyzer
~/.openclaw/skills/deck-analyzer/deck-analyzer test
```

## Technical Details

- **Language:** Python 3
- **AI Model:** Claude Haiku 4.5 (fast, cost-effective)
- **Dependencies:** requests (HTTP client)
- **Timeout:** 60 seconds per analysis
- **Content limit:** First 20,000 characters of deck

## Output Format

**JSON format** for programmatic use:
```json
{
  "company_name": "...",
  "product_overview": "...",
  ...
}
```

**HubSpot format** for CRM entry:
```
PRODUCT: AI-powered workflow automation platform

PROBLEM/SOLUTION: Companies waste 40% of time on manual tasks...

KEY CAPABILITIES: Natural language automation, integration hub...

TEAM: CEO: ex-Google AI, CTO: ex-Microsoft Azure

GTM STRATEGY: Enterprise B2B, starting with Fortune 500

TRACTION: 3 pilot customers, $50K ARR

FUNDRAISING: Raising $2M seed round
```

## Use Cases

### Quick Deck Review
Before a meeting, quickly extract key info from a deck:
```bash
deck-analyzer analyze https://docsend.com/view/abc123
```

### Automated Deal Enrichment
When deal-logger finds a deck in an email, automatically analyze it:
```python
deck_info = analyze_deck(deck_url, sender_email)
company_description = format_company_description(deck_info)
# Add to HubSpot deal
```

### Batch Deck Processing
Process multiple decks from a list:
```bash
while read url; do
  deck-analyzer analyze "$url"
done < deck_urls.txt
```

## Limitations

- **DocSend authentication:** Some DocSend links require email verification
- **Content extraction:** Only extracts visible text, not images
- **PDF support:** Basic PDF text extraction (may miss formatted content)
- **Rate limits:** Subject to Claude API rate limits

## Troubleshooting

**"ANTHROPIC_API_KEY not set"**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**DocSend access denied:**
- Try providing sender email: `deck-analyzer analyze URL sender@email.com`
- DocSend may require browser-based authentication

**No information extracted:**
- Deck may be image-based (no text to extract)
- Content may be behind authentication
- Try downloading PDF and analyzing locally

**Timeout errors:**
- Large decks may take longer
- Try again or use a faster network connection

## Privacy & Security

- Deck content is sent to Claude API for analysis
- No deck content is stored permanently
- Authentication cookies are not persisted
- Sender emails only used for DocSend auth requests
