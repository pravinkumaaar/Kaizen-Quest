#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Personal AI Agent — Mac First-Time Setup Script
# Run: bash setup.sh
#
# ✅ Completely free — no Claude Pro, no Claude Code, no credit card
# Everything runs via Python + GitHub Actions + free APIs
# ─────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
step() { echo -e "\n${BLUE}▶ $1${NC}"; }
info() { echo -e "   $1"; }

echo ""
echo "🤖 Personal AI Agent — Free Setup"
echo "════════════════════════════════════"
echo "No Claude Pro needed. No credit card. \$0/month."
echo ""

# ── Step 1: Homebrew ──────────────────────────────────────────
step "Step 1: Homebrew (Mac package manager)"

if ! command -v brew &>/dev/null; then
  warn "Homebrew not found — installing now..."
  info "This will ask for your Mac password. That is normal."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -f "/opt/homebrew/bin/brew" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
  elif [[ -f "/usr/local/bin/brew" ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  ok "Homebrew installed"
else
  ok "Homebrew: $(brew --version | head -1)"
fi

# ── Step 2: Python ────────────────────────────────────────────
step "Step 2: Python 3"

if ! command -v python3 &>/dev/null; then
  brew install python && ok "Python installed"
else
  ok "Python: $(python3 --version)"
fi

# ── Step 3: Git ───────────────────────────────────────────────
step "Step 3: Git"

if ! command -v git &>/dev/null; then
  brew install git && ok "Git installed"
else
  ok "Git: $(git --version)"
fi

# ── Step 4: Python packages ───────────────────────────────────
step "Step 4: Installing Python packages"
info "feedparser, requests, yfinance, openai, python-dotenv, pandas, numpy"

INSTALL_OK=false
if pip3 install -r requirements.txt --quiet --no-warn-script-location 2>/dev/null; then
  INSTALL_OK=true
elif python3 -m pip install -r requirements.txt --quiet 2>/dev/null; then
  INSTALL_OK=true
elif pip3 install -r requirements.txt --user --quiet 2>/dev/null; then
  INSTALL_OK=true
fi

if python3 -c "import feedparser, requests, yfinance, openai" 2>/dev/null; then
  ok "All Python packages ready"
else
  warn "Package install had issues. Try manually: pip3 install -r requirements.txt"
fi

# ── Step 5: Folders ───────────────────────────────────────────
step "Step 5: Creating project folders"
mkdir -p REPORTS HISTORY logs
ok "Created: REPORTS/ HISTORY/ logs/"

# ── Step 6: .env file ─────────────────────────────────────────
step "Step 6: Setting up .env file"

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    ok ".env created from .env.example"
  else
    printf 'OPENROUTER_API_KEY=sk-or-v1-your-key-here\nTAVILY_API_KEY=tvly-your-key-here\nFINNHUB_API_KEY=your-finnhub-key-here\nOPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free\n' > .env
    ok ".env created from scratch"
  fi
  warn "Edit .env and add your real API keys before running the agent"
else
  ok ".env already exists — skipping"
fi

# ── Step 7: Quick tests ───────────────────────────────────────
step "Step 7: Running quick tests"

PRICE=$(python3 -c "
import os
finnhub_key = os.environ.get('FINNHUB_API_KEY')
if finnhub_key:
    import requests
    try:
        r = requests.get(f'https://finnhub.io/api/v1/quote?symbol=SPY&token={finnhub_key}', timeout=10)
        data = r.json()
        p = data.get('c')
        print(f'{p:.2f}' if p else 'error')
    except:
        print('error')
else:
    import yfinance as yf
    try:
        p = yf.Ticker('SPY').fast_info.last_price
        print(f'{p:.2f}')
    except:
        print('error')
" 2>/dev/null)

if [[ "$PRICE" == "error" ]] || [[ -z "$PRICE" ]]; then
  warn "yfinance test failed (check internet)"
else
  ok "Market data working — SPY: \$$PRICE"
fi

RSS_OK=$(python3 -c "
import feedparser
f = feedparser.parse('https://techcrunch.com/feed/')
print('ok' if f.entries else 'empty')
" 2>/dev/null)
[[ "$RSS_OK" == "ok" ]] && ok "RSS feeds working" || warn "RSS test failed"

# Load .env safely for key test
if [ -f ".env" ]; then
  while IFS='=' read -r key val; do
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue
    export "$key"="$val" 2>/dev/null || true
  done < .env
fi

if [ -n "$OPENROUTER_API_KEY" ] && [ "$OPENROUTER_API_KEY" != "sk-or-v1-your-key-here" ]; then
  OPENROUTER_MODEL="${OPENROUTER_MODEL:-qwen/qwen3-next-80b-a3b-instruct:free}"
  LLM_TEST=$(python3 -c "
from openai import OpenAI
import os
try:
    client = OpenAI(api_key='${OPENROUTER_API_KEY}', base_url='https://openrouter.ai/api/v1')
    r = client.chat.completions.create(
        model='${OPENROUTER_MODEL}',
        max_tokens=15,
        messages=[{'role':'user','content':'Reply: online'}]
    )
    print(r.choices[0].message.content.strip()[:40])
except Exception as e:
    print(f'error: {e}')
" 2>/dev/null)
  if [[ "$LLM_TEST" == error* ]]; then
    warn "OpenRouter test failed: $LLM_TEST"
  else
    ok "OpenRouter LLM working — response: $LLM_TEST"
  fi
else
  warn "OpenRouter key not set yet — add it to .env to test"
fi

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════"
echo "🎉 Setup complete!"
echo ""
echo "━━━ NEXT STEPS ━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. GET 3 FREE API KEYS (no credit card, ~10 min total):"
echo ""
echo "   REQUIRED:"
echo "   • OpenRouter: https://openrouter.ai"
echo "     Sign up → Keys → Create key (starts with sk-or-v1-)"
echo ""
echo "   OPTIONAL (but recommended, both free):"
echo "   • Tavily:     https://tavily.com   (web search, 1000/month free)"
echo "   • Finnhub:    https://finnhub.io   (market news, 60/min free)"
echo ""
echo "2. ADD KEYS TO .env:"
echo "   Open the .env file in TextEdit and paste your keys"
echo "   (safe — this file never uploads to GitHub)"
echo ""
echo "3. TEST LOCALLY:"
echo "   python3 agent.py"
echo "   Then check REPORTS/ for your first report"
echo ""
echo "4. PUSH TO GITHUB + ADD SECRETS:"
echo "   git add . && git commit -m 'setup' && git push"
echo "   GitHub repo → Settings → Secrets → Actions → add same 3 keys"
echo ""
echo "5. TRIGGER FIRST CLOUD RUN:"
echo "   GitHub repo → Actions → daily-agent → Run workflow"
echo ""
echo "━━━ COST ━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Now:    ~\$1-2/month (DeepSeek Chat on OpenRouter)"
echo "   Free:   Switch to qwen/qwen3-coder:free if needed"
echo "           = \$0/month but with rate limits"
echo "════════════════════════════════════"
