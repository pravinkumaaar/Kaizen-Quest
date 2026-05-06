"""
Earnings Intelligence Skill v2.0

Comprehensive earnings analysis covering:
1. FULL Finnhub earnings calendar sweep (not just a curated list)
2. Forward-looking estimates: EPS/revenue estimates vs consensus
3. Earnings surprise history (do they consistently beat/miss?)
4. Options implications: expected moves, IV crush opportunities
5. Sector-wide earnings momentum signals

Uses Finnhub free tier APIs:
  - /calendar/earnings: Full earnings calendar (~5000 companies/week)
  - /stock/earnings: Historical earnings & surprises
  - /stock/recommendation: Analyst recommendations
  - /stock/price-target: Price targets vs current price
  - /stock/metric: Fundamental metrics
"""

import requests
import json
import csv
import datetime
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None

# ─────────────────────────────────────────────
# COMPREHENSIVE UNIVERSE
# ─────────────────────────────────────────────
# This is the full list of stocks we track for earnings intelligence.
# Covers: S&P 500 top 100, Nasdaq-100, high-beta movers, sector leaders,
# emerging growth, and companies with significant options activity.

EARNINGS_UNIVERSE = [
    # ═══════════════════════════════════════════
    # MEGA-CAP TECH (always relevant)
    # ═══════════════════════════════════════════
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA",
    # ═══════════════════════════════════════════
    # SEMICONDUCTORS / AI INFRASTRUCTURE
    # ═══════════════════════════════════════════
    "AMD", "INTC", "TSM", "AVGO", "QCOM", "MU", "MRVL", "AMAT", "LRCX",
    "KLAC", "SNPS", "CDNS", "ARM", "ASML", "NXPI", "MCHP", "SWKS",
    "QRVO", "ON", "GFS", "MPWR", "RMBS", "SLAB", "POWI", "DIOD",
    "ALGM", "SITM", "TTMI", "OLED", "KLIC", "TER", "COHR", "MKSI",
    "BRKS", "ENTG", "WOLF", "ACLS", "AMKR", "FORM", "PLAB", "UCTT",
    "VECO", "XPER", "CRUS", "MXL", "SIMO", "AAOI", "LITE", "CIEN",
    "INFN", "ADTN", "CALX", "ITRI", "DGII", "AVNW", "COMM", "VIAV",
    "EXFO", "BDC", "PI", "SYPR", "MEI", "FLEX", "JBL", "SANM",
    "TTMI", "BHE", "CTS", "ELTK", "KOPN", "EMAN", "LPTH", "LGL",
    # ═══════════════════════════════════════════
    # CLOUD / SAAS / SOFTWARE
    # ═══════════════════════════════════════════
    "CRM", "NOW", "SNOW", "PLTR", "NET", "DDOG", "MDB", "WDAY", "ZS",
    "CRWD", "OKTA", "PANW", "S", "AI", "PATH", "ASAN", "ZM", "TEAM",
    "HUBS", "VEEV", "DOCU", "COUP", "ZUO", "BILL", "NCNO", "SUMO",
    "QLYS", "TENB", "VRNS", "RPD", "SWI", "BLKB", "ALTR", "APPN",
    "MNDY", "AVDX", "BL", "DV", "PRO", "WK", "LSPD", "RAMP",
    "APPF", "ALKT", "EVBG", "FROG", "KLTR", "MITK", "PRGS", "QTWO",
    "RNG", "SMAR", "TDC", "VRNT", "WKME", "XM", "YALA", "ZUO",
    "BIGC", "BMBL", "BTBT", "CFLT", "CSGS", "CSLT", "DLO", "DOCN",
    "DOMO", "DSGX", "DT", "EB", "ECOM", "ENV", "ESTC", "EVCM",
    "FICO", "FOUR", "GDRX", "GEN", "GLOB", "GSB", "GTLB", "HCAT",
    "HCP", "HKD", "IBEX", "INFA", "INST", "INTA", "JAMF", "KAR",
    "KC", "LIFW", "LPSN", "MANH", "MCW", "MLNK", "MODN", "MTTR",
    "NCNO", "NICE", "NOVA", "NUAN", "OLO", "OSPN", "PAYC", "PD",
    "PCTY", "PING", "PMTS", "PRFT", "PSFE", "PWSC", "QADA", "RAMP",
    "RPD", "SABR", "SAIL", "SCWX", "SEMR", "SGFY", "SHOP", "SIMO",
    "SKLZ", "SLQT", "SMAR", "SMSI", "SPT", "SPWR", "SQSP", "STEM",
    "STNE", "TENB", "TIXT", "TOST", "TRU", "TTD", "TWLO", "U",
    "UPST", "VEEV", "VERX", "VRRM", "WEX", "WK", "WIX", "XM",
    "YALA", "YEXT", "ZEN", "ZI", "ZM", "ZS", "ZUO",
    # ═══════════════════════════════════════════
    # FINANCIALS / FINTECH / PAYMENTS
    # ═══════════════════════════════════════════
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP",
    "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "AFRM", "SOFI", "UPST",
    "LC", "OPFI", "NU", "NUVB", "NUWE", "ALLY", "DFS", "SYF", "COF",
    "BK", "STT", "TFC", "USB", "PNC", "RF", "CFG", "HBAN", "FITB",
    "KEY", "MTB", "CMA", "ZION", "WAL", "EWBC", "UMPQ", "BANF",
    "FFIN", "TCBI", "SFBS", "ABCB", "AUB", "BKU", "BOH", "CBSH",
    "CFR", "CHCO", "CTBI", "CVBF", "EBC", "EFSC", "EGBN", "ESNT",
    "FBK", "FFBC", "FFWM", "FHB", "FISI", "FLIC", "FMBH", "FULT",
    "GABC", "GBCI", "GSBC", "HAFC", "HBNC", "HBT", "HFWA", "HWC",
    "HOMB", "HTLF", "HTBK", "IBCP", "IBOC", "INDB", "ISBC", "LBAI",
    "LKFN", "MBCN", "MCB", "MCBC", "MOFG", "MPB", "MSBI", "MTG",
    "NMIH", "NRIM", "NWBI", "OCFC", "OFG", "ONB", "OPBK", "ORI",
    "OZK", "PB", "PFBC", "PFIS", "PFS", "PPBI", "PRK", "PSTG",
    "QCRH", "RBCAA", "RBNC", "RNST", "SASR", "SBCF", "SBFG", "SBSI",
    "SF", "SFNC", "SFST", "SHBI", "SIVB", "SLM", "SMBK", "SMBC",
    "SMMF", "SNV", "SPFI", "SRCE", "SSB", "STBA", "STEL", "STL",
    "STLD", "TCBK", "TCF", "TCOM", "THFF", "TMP", "TRMK", "TRST",
    "TSC", "UBSI", "UCBI", "UCBIO", "UHT", "UMBF", "UMPQ", "UNB",
    "UNTY", "USB", "UVSP", "VBTX", "VLY", "WABC", "WAFD", "WAL",
    "WASH", "WBS", "WD", "WTBA", "WTFC",
    # Insurance
    "AIG", "MET", "PRU", "ALL", "TRV", "CB", "PGR", "CINF", "WRB",
    "L", "RE", "RNR", "AIZ", "FAF", "FNF", "RKT", "VOYA", "UNM",
    "AFL", "GL", "PFG", "LNC", "PRU", "MET", "AIG",
    # ═══════════════════════════════════════════
    # HEALTHCARE / PHARMA / BIOTECH
    # ═══════════════════════════════════════════
    "JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "GILD", "AMGN", "REGN",
    "VRTX", "BIIB", "NVO", "MRNA", "BNTX", "TXN", "KRYS", "SRPT",
    "BMRN", "INCY", "HALO", "EXEL", "NBIX", "ALNY", "ARWR", "NTLA",
    "BEAM", "EDIT", "CRSP", "VTRS", "PBH", "PRGO", "TEVA", "ZTS",
    "IDXX", "WST", "TFX", "PEN", "GMED", "NUVA", "ARVN", "TMDX",
    "INSP", "IRTC", "ABMD", "BSX", "EW", "DXCM", "PODD", "SWAV",
    "LMAT", "AXNX", "KIDS", "CNMD", "UFPI", "ICUI", "HAE", "ATR",
    "RMD", "STE", "ZBH", "SYK", "MDT", "ABT", "DHR", "TMO", "A",
    "LH", "DGX", "IQV", "MTD", "WAT", "PKI", "BIO", "TECH", "CTLT",
    "MEDP", "NVCR", "HOLX", "ISRG", "INTU",
    # Healthcare services
    "UNH", "CI", "HUM", "ELV", "MOH", "CNC", "MOH", "WCG", "AGL",
    "PINC", "AMED", "LHCG", "CHE", "DGX", "LH",
    # Medical devices
    "ISRG", "SYK", "BSX", "MDT", "ABT", "DHR", "TMO", "ZBH", "EW",
    "PEN", "GMED", "NUVA", "ARVN", "TMDX", "INSP", "IRTC", "SWAV",
    "LMAT", "AXNX", "KIDS", "CNMD", "UFPI", "ICUI", "HAE", "ATR",
    "RMD", "STE", "HOLX", "DXCM", "PODD",
    # ═══════════════════════════════════════════
    # CONSUMER / RETAIL / E-COMMERCE
    # ═══════════════════════════════════════════
    "WMT", "COST", "HD", "LOW", "TGT", "DG", "DLTR", "ROST", "TJX",
    "ORLY", "AZO", "AAP", "GPC", "MRO", "DKS", "CVS", "RAD", "YUM",
    "MCD", "SBUX", "DPZ", "CMG", "WING", "SHAK", "CAVA", "TXRH",
    "DRI", "BLMN", "DENN", "PZZA", "FIVE", "OLLI", "SFM", "IMKTA",
    "NGVT", "PFGC", "USFD", "UNFI", "ANDE", "CALM", "TSN", "PPC",
    "HRL", "CAG", "CPB", "GIS", "HSY", "KHC", "MKC", "SJM", "CL",
    "PG", "CHD", "CLX", "EL", "KMB", "COTY", "ELF", "IPAR", "NUS",
    "USNA", "HLF", "NHTC", "MED", "NATR", "RELV", "MTEX",
    # Apparel / Footwear
    "NKE", "ADDYY", "LULU", "DECK", "ONON", "CROX", "SKX", "COLM",
    "VFC", "RL", "PVH", "UAA", "UA", "HBI", "GIL", "GOOS", "MONCLER",
    # E-Commerce / Digital
    "AMZN", "SHOP", "WIX", "SE", "MELI", "ETSY", "CPNG", "GLBE",
    "DTC", "OLPX", "REAL", "CART", "MELI", "SE", "SHOP", "WIX",
    "SQSP", "RDFN", "Z", "OPEN", "RMAX", "EXPI", "COMP", "OPAD",
    # Travel / Leisure
    "ABNB", "BKNG", "RCL", "CCL", "NCLH", "MAR", "HLT", "WH", "H",
    "IHG", "CHH", "WH", "MAR", "HLT", "H", "IHG", "CHH", "HTHT",
    "TCOM", "DAL", "AAL", "UAL", "LUV", "JBLU", "ALK", "SAVE",
    "MESA", "ULCC", "HA", "SKYW", "CPA", "ERJ", "LTM", "ALGT",
    # ═══════════════════════════════════════════
    # ENERGY / OIL & GAS / CLEAN ENERGY
    # ═══════════════════════════════════════════
    "XOM", "CVX", "COP", "EOG", "PXD", "SLB", "BKR", "HAL", "OXY",
    "MPC", "VLO", "PSX", "DK", "PAR", "SUN", "CVI", "DINO", "VTLE",
    "GPRE", "CLNE", "BLDP", "FCEL", "PLUG", "BE", "ICLN", "QCLN",
    "PBW", "LIT", "REMX", "URA", "SMH", "XME", "KRE", "XOP", "IEO",
    "OIH", "XES", "FANG", "DVN", "MRO", "APA", "RRC", "SWN", "AR",
    "CHK", "CRK", "MTDR", "TALO", "WDS", "STO", "EQNR", "TTE", "SHEL",
    "BP", "E", "VLO", "MPC", "PSX", "DK", "PAR", "SUN", "CVI", "DINO",
    # Clean energy
    "ENPH", "SEDG", "FSLR", "SPWR", "CSIQ", "JKS", "NXT", "ARRY",
    "MAXN", "SHLS", "GPRE", "CLNE", "BLDP", "FCEL", "PLUG", "BE",
    "ICLN", "QCLN", "PBW", "LIT", "REMX", "URA",
    # ═══════════════════════════════════════════
    # INDUSTRIALS / DEFENSE / AEROSPACE
    # ═══════════════════════════════════════════
    "CAT", "DE", "URI", "PCAR", "CMI", "AME", "ETN", "PH", "ITW",
    "DOV", "IR", "DAL", "AAL", "UAL", "LUV", "CCJ", "NEM", "GOLD",
    "AEM", "WPM", "FNV", "KGC", "AGI", "AUY", "HMY", "GFI", "EDR",
    "OR", "IAG", "FRES", "LAC", "SQM", "ALB", "LTHM", "PLL", "MP",
    "CRML", "SGML", "CHPT", "BLNK", "EVGO",
    # Defense
    "LMT", "RTX", "NOC", "GD", "BA", "HII", "TDY", "TXT", "SPR",
    "HEI", "CW", "BWXT", "ESLT", "RADA", "KTOS", "AVAV", "MOG.A",
    "HXL", "TGI", "MRCY", "DRS", "ACHR", "JOBY", "VLDR", "EH",
    "ASTR", "RKLB", "SPIR", "MNTS", "LILM", "SDRD",
    # Industrials
    "GE", "HON", "MMM", "UPS", "FDX", "CSX", "UNP", "NSC", "WAB",
    "ITW", "PH", "ETN", "EMR", "ROP", "OTIS", "CARR", "TT", "JCI",
    "HWM", "CAT", "DE", "PCAR", "CMI", "AME", "DOV", "GGG", "LECO",
    "IEX", "DOV", "GGG", "LECO", "EMR", "ROP", "OTIS", "PH", "CARR",
    "TT", "JCI", "HON", "MMM", "GE", "HWM",
    # ═══════════════════════════════════════════
    # MEDIA / ENTERTAINMENT / GAMING
    # ═══════════════════════════════════════════
    "NFLX", "DIS", "WBD", "PARA", "FOXA", "LYV", "ROKU", "SPOT",
    "TME", "WMG", "NWSA", "LGF.A", "AMC", "CNK", "IMAX", "MANU",
    "FWONA", "SIRI", "POD", "AUD", "IHRT", "SALM", "GTN", "MDIA",
    # Gaming
    "ATVI", "EA", "TTWO", "RBLX", "U", "DKNG", "PENN", "FUN", "MSGS",
    "SE", "NTFY", "PLTK", "GAN", "DKNG", "PENN", "CZR", "LVS", "WYNN",
    "MGM", "BYD", "PENN", "CZR", "LVS", "WYNN", "MGM", "BYD",
    # Social / Digital ads
    "META", "GOOG", "SNAP", "PINS", "TTD", "ROKU", "SPOT",
    # ═══════════════════════════════════════════
    # TELECOM / COMMUNICATION
    # ═══════════════════════════════════════════
    "TMUS", "T", "VZ", "CMCSA", "CHTR", "LUMN", "FYBR", "LILA",
    "AMT", "EQIX", "SBAC", "CCI", "DLR", "EXR", "VTR", "WELL",
    "UNIT", "LTC", "NHI", "OHI", "MPW", "HR", "PEAK", "SBRA",
    # ═══════════════════════════════════════════
    # MATERIALS / CHEMICALS / MINING
    # ═══════════════════════════════════════════
    "LIN", "APD", "ECL", "SHW", "FCX", "NUE", "STLD", "CLF", "X",
    "MT", "PKX", "SCCO", "RIO", "BHP", "VALE", "TECK", "HBM",
    "CENX", "KALU", "CSTM", "WOR", "TGLS", "ZWS", "CCJ", "NEM",
    "GOLD", "AEM", "WPM", "FNV", "KGC", "AGI", "AUY", "HMY", "GFI",
    "EDR", "OR", "IAG", "FRES", "LAC", "SQM", "ALB", "LTHM", "PLL",
    "MP", "CRML", "SGML",
    # ═══════════════════════════════════════════
    # REAL ESTATE / REITs
    # ═══════════════════════════════════════════
    "PLD", "AMT", "EQIX", "DLR", "SPG", "O", "WELL", "VTR", "PSA",
    "EXR", "AVB", "EQR", "MAA", "UDR", "CPT", "BXP", "VNO", "SLG",
    "HIW", "DECU", "KRC", "JBGS", "HPP", "BDN", "PGRE", "ALEX",
    "CMCT", "OPI", "UNIT", "LTC", "NHI", "OHI", "MPW", "HR", "PEAK",
    "SBRA", "CTRE", "GMRE", "CHCT", "DHC", "RHP", "PK", "SHO", "PEB",
    "DRH", "HST", "APLE", "CLDT", "RLJ", "ILPT", "SELF", "GRTA",
    "LAND", "MDRR", "ALEX", "BRT", "CDR", "FPI", "NXRT", "ROIC",
    "RPAI", "RPT", "SKT", "TCO", "UBA", "WRI", "XAN", "AAT", "ADC",
    "AKR", "ALX", "APTS", "BFS", "BRSP", "CBL", "CLDT", "CMCT",
    "CPT", "CTRE", "CUZ", "CXW", "DHC", "DLR", "DRH", "EPR", "EQR",
    "EXR", "FPI", "GMRE", "GRTA", "HPP", "HST", "HT", "IIPR", "ILPT",
    "JBGS", "JLL", "KRC", "LAMR", "LAND", "LTC", "MAA", "MDRR", "MPW",
    "NHI", "NNN", "NRE", "NRZ", "NTST", "NXRT", "O", "OHI", "OPI",
    "PEAK", "PEB", "PK", "PLD", "PSA", "PSB", "REG", "REXR", "RHP",
    "RLJ", "ROIC", "RPAI", "RPT", "RWT", "SBRA", "SELF", "SHO",
    "SKT", "SLG", "SPG", "STAG", "STOR", "TCO", "UBA", "UDR", "UNIT",
    "VICI", "VNO", "VTR", "WELL", "WPC", "WRI", "XAN",
    # ═══════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "PEG",
    "AWK", "ES", "ETR", "FE", "CNP", "NI", "LNT", "EIX", "PPL",
    "AES", "AGR", "AMPS", "ARIS", "AQN", "ATO", "AVA", "BKH", "BEP",
    "BEPC", "CEG", "CIG", "CMS", "CPK", "CTRA", "CWEN", "DTE", "EAI",
    "EBR", "EVRG", "FLNC", "FCEL", "GPRE", "HE", "IDA", "KEN", "KEP",
    "KMI", "LNG", "MGEE", "MNTN", "NFG", "NGG", "NJR", "NOVA", "NRG",
    "NTG", "NWE", "OGE", "OGS", "OPAL", "ORA", "OTTR", "PCG", "PCYO",
    "PNM", "PNW", "PPA", "PRP", "PPL", "RGCO", "RNW", "RUG", "SBS",
    "SJI", "SM", "SMLP", "SPH", "SR", "SWX", "TAC", "TPIC", "TPH",
    "TRGP", "TS", "UGI", "UMC", "UTL", "VGAS", "VIA", "VIST", "VST",
    "WEC", "WTRG", "WTRU", "XEL", "ZNH",
    # ═══════════════════════════════════════════
    # CRYPTO-ADJACENT / BLOCKCHAIN
    # ═══════════════════════════════════════════
    "MSTR", "MARA", "RIOT", "COIN", "HOOD", "SQ", "PYPL", "CLSK",
    "BTBT", "HUT", "CORZ", "WULF", "BITF", "SDIG", "IREN", "CIFR",
    "SDIG", "ARBK", "HIVE", "BITF", "WULF", "IREN", "CIFR", "CLSK",
    "BTBT", "HUT", "CORZ",
    # ═══════════════════════════════════════════
    # EV / AUTO / TRANSPORTATION
    # ═══════════════════════════════════════════
    "TSLA", "F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI", "ALV",
    "APTV", "BWA", "TM", "HMC", "NSANY", "RACE", "STLA", "VWAGY",
    "BYDDY", "FSR", "GOEV", "WKHS", "RIDE", "FFIE", "ARVL", "LEV",
    "XL", "ZEV", "CHPT", "BLNK", "EVGO", "WBX", "ABNB",
    # ═══════════════════════════════════════════
    # HIGH-BETA / MOMENTUM / MEME
    # ═══════════════════════════════════════════
    "GME", "AMC", "BB", "NOK", "PLTR", "SOFI", "LCID", "RIVN", "UPST",
    "AFRM", "COIN", "HOOD", "SQ", "DKNG", "PENN", "CZR", "LVS", "WYNN",
    "MGM", "BYD", "RBLX", "U", "SNAP", "PINS", "ROKU", "SPOT", "ZM",
    "DOCU", "SNOW", "DDOG", "NET", "CRWD", "ZS", "OKTA", "PANW",
    "MDB", "WDAY", "NOW", "CRM", "HUBS", "VEEV", "ASAN", "PATH",
    "AI", "PLTR", "SNOW", "DDOG", "MDB", "NET", "ZS", "CRWD", "OKTA",
]

def init_earnings_skill(finnhub_key=None, base_dir=None):
    """Initialize with config from main agent."""
    global FINNHUB_API_KEY, BASE_DIR
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if base_dir:
        BASE_DIR = Path(base_dir)


def _finnhub_get(endpoint, params=None):
    """Make a Finnhub API call with error handling."""
    if not FINNHUB_API_KEY:
        return None
    if params is None:
        params = {}
    params["token"] = FINNHUB_API_KEY
    try:
        r = requests.get(f"https://finnhub.io/api/v1/{endpoint}", params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_full_earnings_calendar(days_ahead=21, days_back=3):
    """
    Fetch the FULL earnings calendar from Finnhub.
    Returns all companies reporting in the date range (~5000/week on free tier).
    """
    today = datetime.date.today()
    from_date = (today - datetime.timedelta(days=days_back)).isoformat()
    to_date = (today + datetime.timedelta(days=days_ahead)).isoformat()
    data = _finnhub_get("calendar/earnings", {"from": from_date, "to": to_date})
    if data:
        return data.get("earningsCalendar", [])
    return []


def get_earnings_estimate(ticker):
    """Get EPS and revenue estimates for a ticker."""
    data = _finnhub_get(f"stock/earnings", {"symbol": ticker, "limit": 4})
    if data and len(data) > 0:
        return data[0]  # Most recent/reporting period
    return None


def get_earnings_surprise_history(ticker, n=8):
    """Get historical earnings surprises for a ticker."""
    data = _finnhub_get(f"stock/earnings", {"symbol": ticker, "limit": n})
    if not data:
        return []
    surprises = []
    for e in data:
        eps_est = e.get("epsEstimate")
        eps_actual = e.get("epsActual")
        rev_est = e.get("revenueEstimate")
        rev_actual = e.get("revenueActual")
        if eps_actual is not None or rev_actual is not None:
            surprises.append({
                "date": e.get("date", ""),
                "epsEstimate": eps_est,
                "epsActual": eps_actual,
                "revenueEstimate": rev_est,
                "revenueActual": rev_actual,
                "hour": e.get("hour", ""),
            })
    return surprises


def get_analyst_recommendations(ticker):
    """Get analyst recommendation trends."""
    data = _finnhub_get(f"stock/recommendation", {"symbol": ticker})
    if data and len(data) > 0:
        return data[0]  # Most recent month
    return None


def get_price_target(ticker):
    """Get analyst price target vs current price."""
    data = _finnhub_get(f"stock/price-target", {"symbol": ticker})
    if data:
        return {
            "targetHigh": data.get("targetHigh", 0),
            "targetLow": data.get("targetLow", 0),
            "targetMean": data.get("targetMean", 0),
            "targetMedian": data.get("targetMedian", 0),
        }
    return None


def analyze_earnings_momentum(ticker):
    """
    Analyze whether a company consistently beats or misses earnings.
    Returns: {
        "beat_rate": float,  # % of recent quarters that were beats
        "avg_eps_surprise_pct": float,
        "avg_rev_surprise_pct": float,
        "trend": "improving" | "deteriorating" | "consistent" | "mixed",
        "signal": str,  # Human-readable signal
    }
    """
    surprises = get_earnings_surprise_history(ticker, n=8)
    if not surprises or len(surprises) < 2:
        return None

    eps_beats = 0
    eps_total = 0
    rev_beats = 0
    rev_total = 0
    eps_surprises = []
    rev_surprises = []

    for s in surprises:
        if s.get("epsEstimate") is not None and s.get("epsActual") is not None:
            try:
                est = float(s["epsEstimate"])
                actual = float(s["epsActual"])
                eps_total += 1
                if actual > est:
                    eps_beats += 1
                if est != 0:
                    eps_surprises.append((actual - est) / abs(est) * 100)
            except (ValueError, TypeError):
                pass
        if s.get("revenueEstimate") is not None and s.get("revenueActual") is not None:
            try:
                est = float(s["revenueEstimate"])
                actual = float(s["revenueActual"])
                rev_total += 1
                if actual > est:
                    rev_beats += 1
                if est != 0:
                    rev_surprises.append((actual - est) / est * 100)
            except (ValueError, TypeError):
                pass

    beat_rate = (eps_beats / eps_total * 100) if eps_total > 0 else 0
    avg_eps_surprise = sum(eps_surprises) / len(eps_surprises) if eps_surprises else 0
    avg_rev_surprise = sum(rev_surprises) / len(rev_surprises) if rev_surprises else 0

    # Determine trend
    if len(eps_surprises) >= 4:
        recent = eps_surprises[:2]
        older = eps_surprises[2:4]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        if recent_avg > older_avg + 2:
            trend = "improving"
        elif recent_avg < older_avg - 2:
            trend = "deteriorating"
        else:
            trend = "consistent"
    else:
        trend = "mixed"

    # Build signal
    if beat_rate >= 75 and avg_eps_surprise > 3:
        signal = f"Strong beat history ({beat_rate:.0f}%, avg +{avg_eps_surprise:.1f}% EPS surprise)"
    elif beat_rate >= 50 and avg_eps_surprise > 0:
        signal = f"Usually beats ({beat_rate:.0f}%, avg +{avg_eps_surprise:.1f}% EPS surprise)"
    elif beat_rate < 25:
        signal = f"Frequently misses ({beat_rate:.0f}%, avg {avg_eps_surprise:.1f}% EPS surprise)"
    else:
        signal = f"Mixed record ({beat_rate:.0f}%, avg {avg_eps_surprise:+.1f}% EPS surprise)"

    return {
        "beat_rate": beat_rate,
        "avg_eps_surprise_pct": avg_eps_surprise,
        "avg_rev_surprise_pct": avg_rev_surprise,
        "trend": trend,
        "signal": signal,
        "quarters_analyzed": eps_total,
    }


def get_comprehensive_earnings_intelligence(portfolio_tickers=None, days_ahead=21):
    """
    Main entry point: comprehensive earnings intelligence.
    
    Returns dict with:
      - portfolio_earnings: upcoming earnings for your holdings
      - related_earnings: earnings for supply chain / ecosystem companies
      - sector_earnings: earnings for companies in your sectors (comprehensive)
      - forward_analysis: beat/miss predictions for key upcoming earnings
      - options_implications: expected moves and options strategies
      - earnings_surprises: recent earnings surprises (beat/miss)
    """
    if portfolio_tickers is None:
        portfolio_tickers = set()
    else:
        portfolio_tickers = set(t.upper() for t in portfolio_tickers)

    today = datetime.date.today()
    all_calendar = get_full_earnings_calendar(days_ahead=days_ahead)

    # ── Categorize all earnings ──
    portfolio_earnings = []
    related_earnings = []
    sector_earnings = []
    forward_analysis_candidates = []

    # Build universe set for quick lookup
    universe_set = set(EARNINGS_UNIVERSE)

    for e in all_calendar:
        ticker = e.get("symbol", "").upper()
        if not ticker:
            continue

        earnings_date = e.get("date", "")
        try:
            e_dt = datetime.date.fromisoformat(earnings_date)
            days_until = (e_dt - today).days
        except ValueError:
            continue

        if days_until < -3 or days_until > days_ahead:
            continue

        hour = e.get("hour", "")
        eps_est = e.get("epsEstimate", "")
        rev_est = e.get("revenueEstimate", "")

        status = "REPORTED" if days_until < 0 else "TODAY" if days_until == 0 else f"in {days_until}d"
        detail = f" ({hour})" if hour else ""
        if eps_est:
            try:
                detail += f" EPS est: ${float(eps_est):.2f}"
            except (ValueError, TypeError):
                detail += f" EPS est: ${eps_est}"
        if rev_est:
            try:
                rv = float(rev_est)
                if rv > 1e9:
                    detail += f" Rev est: ${rv/1e9:.1f}B"
                else:
                    detail += f" Rev est: ${rv/1e6:.0f}M"
            except (ValueError, TypeError):
                pass

        entry = f"  🔔 {ticker} — Earnings {status} ({earnings_date}){detail}"

        if ticker in portfolio_tickers:
            portfolio_earnings.append(entry)
        elif ticker in universe_set:
            # Check if it's a related/supply chain company
            is_related = False
            for pt in portfolio_tickers:
                if pt in ticker or ticker in pt:
                    is_related = True
                    break
            if is_related:
                related_earnings.append(entry)
            else:
                sector_earnings.append(entry)
        # Also include any company with significant revenue (>$1B) as sector earnings
        elif rev_est:
            try:
                if float(rev_est) > 1e9:
                    sector_earnings.append(entry)
            except (ValueError, TypeError):
                pass

        # Candidates for forward analysis: upcoming earnings for universe companies
        if 0 <= days_until <= 14 and ticker in universe_set:
            forward_analysis_candidates.append({
                "ticker": ticker,
                "date": earnings_date,
                "days_until": days_until,
                "eps_est": eps_est,
                "rev_est": rev_est,
                "hour": hour,
            })

    # ── Forward-looking analysis for top candidates ──
    # Limit to top 15 to avoid rate limits (Finnhub free = 60 req/min)
    forward_analysis = []
    for candidate in sorted(forward_analysis_candidates, key=lambda x: x["days_until"])[:15]:
        ticker = candidate["ticker"]
        momentum = analyze_earnings_momentum(ticker)
        if momentum:
            price_target = get_price_target(ticker)
            rec = get_analyst_recommendations(ticker)

            analysis = {
                "ticker": ticker,
                "date": candidate["date"],
                "days_until": candidate["days_until"],
                "eps_est": candidate["eps_est"],
                "momentum": momentum,
                "price_target": price_target,
                "recommendation": rec,
            }
            forward_analysis.append(analysis)

    # ── Recent earnings surprises ──
    recent_surprises = []
    for e in all_calendar[:50]:  # Check recent entries
        ticker = e.get("symbol", "").upper()
        eps_actual = e.get("epsActual")
        eps_est = e.get("epsEstimate")
        rev_actual = e.get("revenueActual")
        rev_est = e.get("revenueEstimate")
        if eps_actual or rev_actual:
            surprise_parts = []
            if eps_est and eps_actual:
                try:
                    diff = (float(eps_actual) - float(eps_est)) / abs(float(eps_est)) * 100
                    surprise_parts.append(f"EPS {'beat' if diff > 0 else 'missed'} {abs(diff):.1f}%")
                except (ValueError, ZeroDivisionError):
                    pass
            if rev_est and rev_actual:
                try:
                    diff = (float(rev_actual) - float(rev_est)) / float(rev_est) * 100
                    surprise_parts.append(f"Rev {'beat' if diff > 0 else 'missed'} {abs(diff):.1f}%")
                except (ValueError, ZeroDivisionError):
                    pass
            if surprise_parts:
                recent_surprises.append(f"  📊 {ticker} — {', '.join(surprise_parts)}")

    # ── Format output strings ──
    portfolio_str = ""
    if portfolio_earnings:
        portfolio_str = "**📅 Earnings — Your Portfolio Holdings:**\n" + "\n".join(portfolio_earnings) + "\n"

    related_str = ""
    if related_earnings:
        related_str = "**📅 Earnings — Related / Supply Chain Companies:**\n" + "\n".join(related_earnings) + "\n"

    sector_str = ""
    if sector_earnings:
        sector_str = "**📅 Earnings — Comprehensive Sector Coverage:**\n" + "\n".join(sector_earnings) + "\n"

    forward_str = ""
    if forward_analysis:
        lines = ["**🔮 Forward-Looking Earnings Analysis (Beat/Miss Predictions):**"]
        for fa in forward_analysis:
            t = fa["ticker"]
            m = fa["momentum"]
            pt = fa.get("price_target", {})
            r = fa.get("recommendation", {})

            line = f"\n### {t} (Earnings {fa['date']}, in {fa['days_until']}d)"
            line += f"\n  📈 Signal: {m['signal']}"
            line += f"\n  📊 Trend: {m['trend']} ({m['quarters_analyzed']} quarters analyzed)"

            if pt:
                mean = pt.get("targetMean", 0)
                if mean:
                    line += f"\n  🎯 Avg Price Target: ${mean:.2f}"

            if r:
                buy = r.get("strongBuy", 0) + r.get("buy", 0)
                hold = r.get("hold", 0)
                sell = r.get("sell", 0) + r.get("strongSell", 0)
                total = buy + hold + sell
                if total > 0:
                    line += f"\n  👥 Analysts: {buy} Buy / {hold} Hold / {sell} Sell"

            # Options implication
            if m["beat_rate"] >= 75 and m["avg_eps_surprise_pct"] > 3:
                line += f"\n  💡 Options: History of beating → consider buying calls before earnings or selling puts. IV may be elevated — consider selling premium if you expect a beat but not a huge move."
            elif m["beat_rate"] <= 25:
                line += f"\n  💡 Options: History of missing → consider buying puts before earnings or selling calls. Watch for IV crush on any positive surprise."
            elif m["trend"] == "improving":
                line += f"\n  💡 Options: Improving trend → momentum play. Consider calls if you believe the beat streak continues."
            else:
                line += f"\n  💡 Options: Mixed record → consider straddles/strangles if you expect a big move but direction is uncertain."

            lines.append(line)

        forward_str = "\n".join(lines) + "\n"

    surprises_str = ""
    if recent_surprises:
        surprises_str = "**📊 Recent Earnings Surprises (Beat/Miss):**\n" + "\n".join(recent_surprises[:15]) + "\n"

    return {
        "portfolio_earnings": portfolio_str,
        "related_earnings": related_str,
        "sector_earnings": sector_str,
        "forward_analysis": forward_str,
        "recent_surprises": surprises_str,
        "all_calendar_entries": all_calendar,
    }


__all__ = [
    "init_earnings_skill",
    "get_comprehensive_earnings_intelligence",
    "get_full_earnings_calendar",
    "analyze_earnings_momentum",
    "get_earnings_surprise_history",
    "get_analyst_recommendations",
    "get_price_target",
    "EARNINGS_UNIVERSE",
]
