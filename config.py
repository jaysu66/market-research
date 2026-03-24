"""品类配置和州信息"""

# 美国50州 + DC
US_STATES = {
    "AL": {"name": "Alabama", "fips": "01", "cities": ["Birmingham", "Montgomery", "Huntsville", "Mobile"]},
    "AK": {"name": "Alaska", "fips": "02", "cities": ["Anchorage", "Fairbanks", "Juneau"]},
    "AZ": {"name": "Arizona", "fips": "04", "cities": ["Phoenix", "Tucson", "Mesa", "Scottsdale"]},
    "AR": {"name": "Arkansas", "fips": "05", "cities": ["Little Rock", "Fort Smith", "Fayetteville"]},
    "CA": {"name": "California", "fips": "06", "cities": ["Los Angeles", "San Francisco", "San Diego", "San Jose"]},
    "CO": {"name": "Colorado", "fips": "08", "cities": ["Denver", "Colorado Springs", "Aurora", "Fort Collins"]},
    "CT": {"name": "Connecticut", "fips": "09", "cities": ["Bridgeport", "New Haven", "Hartford", "Stamford"]},
    "DE": {"name": "Delaware", "fips": "10", "cities": ["Wilmington", "Dover", "Newark"]},
    "FL": {"name": "Florida", "fips": "12", "cities": ["Miami", "Orlando", "Tampa", "Jacksonville"]},
    "GA": {"name": "Georgia", "fips": "13", "cities": ["Atlanta", "Augusta", "Savannah", "Columbus"]},
    "HI": {"name": "Hawaii", "fips": "15", "cities": ["Honolulu", "Hilo", "Kailua"]},
    "ID": {"name": "Idaho", "fips": "16", "cities": ["Boise", "Meridian", "Nampa"]},
    "IL": {"name": "Illinois", "fips": "17", "cities": ["Chicago", "Aurora", "Naperville", "Rockford"]},
    "IN": {"name": "Indiana", "fips": "18", "cities": ["Indianapolis", "Fort Wayne", "Evansville", "South Bend"]},
    "IA": {"name": "Iowa", "fips": "19", "cities": ["Des Moines", "Cedar Rapids", "Davenport"]},
    "KS": {"name": "Kansas", "fips": "20", "cities": ["Wichita", "Overland Park", "Kansas City", "Topeka"]},
    "KY": {"name": "Kentucky", "fips": "21", "cities": ["Louisville", "Lexington", "Bowling Green"]},
    "LA": {"name": "Louisiana", "fips": "22", "cities": ["New Orleans", "Baton Rouge", "Shreveport"]},
    "ME": {"name": "Maine", "fips": "23", "cities": ["Portland", "Lewiston", "Bangor"]},
    "MD": {"name": "Maryland", "fips": "24", "cities": ["Baltimore", "Columbia", "Germantown", "Silver Spring"]},
    "MA": {"name": "Massachusetts", "fips": "25", "cities": ["Boston", "Worcester", "Springfield", "Cambridge"]},
    "MI": {"name": "Michigan", "fips": "26", "cities": ["Detroit", "Grand Rapids", "Ann Arbor", "Lansing"]},
    "MN": {"name": "Minnesota", "fips": "27", "cities": ["Minneapolis", "Saint Paul", "Rochester", "Duluth"]},
    "MS": {"name": "Mississippi", "fips": "28", "cities": ["Jackson", "Gulfport", "Southaven"]},
    "MO": {"name": "Missouri", "fips": "29", "cities": ["Kansas City", "Saint Louis", "Springfield", "Columbia"]},
    "MT": {"name": "Montana", "fips": "30", "cities": ["Billings", "Missoula", "Great Falls"]},
    "NE": {"name": "Nebraska", "fips": "31", "cities": ["Omaha", "Lincoln", "Bellevue"]},
    "NV": {"name": "Nevada", "fips": "32", "cities": ["Las Vegas", "Henderson", "Reno", "North Las Vegas"]},
    "NH": {"name": "New Hampshire", "fips": "33", "cities": ["Manchester", "Nashua", "Concord"]},
    "NJ": {"name": "New Jersey", "fips": "34", "cities": ["Newark", "Jersey City", "Paterson", "Elizabeth"]},
    "NM": {"name": "New Mexico", "fips": "35", "cities": ["Albuquerque", "Las Cruces", "Santa Fe"]},
    "NY": {"name": "New York", "fips": "36", "cities": ["New York City", "Buffalo", "Rochester", "Syracuse"]},
    "NC": {"name": "North Carolina", "fips": "37", "cities": ["Charlotte", "Raleigh", "Greensboro", "Durham"]},
    "ND": {"name": "North Dakota", "fips": "38", "cities": ["Fargo", "Bismarck", "Grand Forks"]},
    "OH": {"name": "Ohio", "fips": "39", "cities": ["Columbus", "Cleveland", "Cincinnati", "Toledo"]},
    "OK": {"name": "Oklahoma", "fips": "40", "cities": ["Oklahoma City", "Tulsa", "Norman"]},
    "OR": {"name": "Oregon", "fips": "41", "cities": ["Portland", "Salem", "Eugene", "Bend"]},
    "PA": {"name": "Pennsylvania", "fips": "42", "cities": ["Philadelphia", "Pittsburgh", "Allentown", "Erie"]},
    "RI": {"name": "Rhode Island", "fips": "44", "cities": ["Providence", "Warwick", "Cranston"]},
    "SC": {"name": "South Carolina", "fips": "45", "cities": ["Charleston", "Columbia", "Greenville"]},
    "SD": {"name": "South Dakota", "fips": "46", "cities": ["Sioux Falls", "Rapid City", "Aberdeen"]},
    "TN": {"name": "Tennessee", "fips": "47", "cities": ["Nashville", "Memphis", "Knoxville", "Chattanooga"]},
    "TX": {"name": "Texas", "fips": "48", "cities": ["Houston", "Dallas", "San Antonio", "Austin"]},
    "UT": {"name": "Utah", "fips": "49", "cities": ["Salt Lake City", "West Valley City", "Provo"]},
    "VT": {"name": "Vermont", "fips": "50", "cities": ["Burlington", "South Burlington", "Rutland"]},
    "VA": {"name": "Virginia", "fips": "51", "cities": ["Virginia Beach", "Norfolk", "Richmond", "Arlington"]},
    "WA": {"name": "Washington", "fips": "53", "cities": ["Seattle", "Spokane", "Tacoma", "Vancouver"]},
    "WV": {"name": "West Virginia", "fips": "54", "cities": ["Charleston", "Huntington", "Morgantown"]},
    "WI": {"name": "Wisconsin", "fips": "55", "cities": ["Milwaukee", "Madison", "Green Bay"]},
    "WY": {"name": "Wyoming", "fips": "56", "cities": ["Cheyenne", "Casper", "Laramie"]},
}

# 品类配置
PRODUCTS = {
    "curtains": {
        "display_name": "窗帘/窗饰",
        "en_name": "Window Treatments / Curtains",
        "yelp_term": "window treatments",
        "angi_term": "blinds installation",
        "search_queries": {
            "pricing": [
                'site:angi.com "{angi_term}" "{city}" cost per window "average"',
                'site:angi.com "{angi_term}" "{city2}" cost per window "average"',
            ],
            "rent": [
                'site:cbre.com "retail" "{city}" "asking rent" "per square foot"',
            ],
            "trends": [
                '"{en_name} trends" "2026" "{state}" consumer',
                '"{en_name}" "smart" OR "sustainable" "{state}"',
                '"{en_name}" preferences "{state}" climate',
            ],
            "supply": [
                '"{en_name}" manufacturer supplier "{state}"',
            ],
            "promotion": [
                '"{en_name}" sale "{city}" "free installation" OR "discount"',
            ],
            "competition": [
                '"{en_name}" brand franchise "{state}" market share',
            ],
        },
    },
    "carpet": {
        "display_name": "地毯",
        "en_name": "Carpet / Flooring",
        "yelp_term": "carpet flooring",
        "angi_term": "carpet installation",
        "search_queries": {
            "pricing": [
                'site:angi.com "{angi_term}" "{city}" cost per square foot',
                'site:angi.com "{angi_term}" "{city2}" cost per square foot',
            ],
            "rent": [
                'site:cbre.com "retail" "{city}" "asking rent" "per square foot"',
            ],
            "trends": [
                '"{en_name} trends" "2026" "{state}" consumer',
                '"{en_name}" "sustainable" OR "eco-friendly" "{state}"',
                '"{en_name}" preferences "{state}" home renovation',
            ],
            "supply": [
                '"{en_name}" manufacturer supplier "{state}"',
            ],
            "promotion": [
                '"{en_name}" sale "{city}" "free installation" OR "discount"',
            ],
            "competition": [
                '"{en_name}" brand franchise "{state}" market share',
            ],
        },
    },
}

# 可信度白名单
TRUSTED_SOURCES = {
    "tier1_government": ["census.gov", "bls.gov", "fred.stlouisfed.org", "data.gov"],
    "tier1_industry": ["angi.com", "homeadvisor.com", "thumbtack.com", "cbre.com", "jll.com"],
    "tier1_platform": ["yelp.com", "houzz.com", "bbb.org"],
    "tier2_media": ["reuters.com", "bloomberg.com", "windowcoveringmag.com", "furnituretoday.com"],
}

BLOCKED_PATTERNS = [
    r"top\d+best.*\.com",
    r".*affiliate.*",
    r".*\.blogspot\.com",
]

# Foursquare 品类映射
FOURSQUARE_CATEGORIES = {
    "curtains": "19038",  # Home Services > Window Treatment
    "carpet": "19005",    # Home Services > Flooring
}

# FRED Series ID 前缀（州缩写替换 XX）
FRED_SERIES = {
    "gdp": "XXNGSP",           # 州名义GDP
    "unemployment": "XXUR",     # 州失业率
    "building_permits": "XXBPPRIVSA",  # 州建筑许可
}

# BLS Area Codes (FIPS -> BLS area code mapping for major states)
BLS_AREA_CODES = {
    "01": "0000001", "02": "0000002", "04": "0000004", "05": "0000005",
    "06": "0000006", "08": "0000008", "09": "0000009", "10": "0000010",
    "12": "0000012", "13": "0000013", "15": "0000015", "16": "0000016",
    "17": "0000017", "18": "0000018", "19": "0000019", "20": "0000020",
    "21": "0000021", "22": "0000022", "23": "0000023", "24": "0000024",
    "25": "0000025", "26": "0000026", "27": "0000027", "28": "0000028",
    "29": "0000029", "30": "0000030", "31": "0000031", "32": "0000032",
    "33": "0000033", "34": "0000034", "35": "0000035", "36": "0000036",
    "37": "0000037", "38": "0000038", "39": "0000039", "40": "0000040",
    "41": "0000041", "42": "0000042", "44": "0000044", "45": "0000045",
    "46": "0000046", "47": "0000047", "48": "0000048", "49": "0000049",
    "50": "0000050", "51": "0000051", "53": "0000053", "54": "0000054",
    "55": "0000055", "56": "0000056",
}

# 州缩写 -> FRED 前缀映射
STATE_ABBR_MAP = {v["fips"]: k for k, v in US_STATES.items()}

# 行业基准数据（用于模型推算）
INDUSTRY_BENCHMARKS = {
    "curtains": {
        "annual_revenue_range": "$600,000 - $1,800,000",
        "custom_gross_margin": "45%-60%",
        "readymade_gross_margin": "20%-30%",
        "design_service_margin": "65%-80%",
        "installation_margin": "50%-65%",
        "rent_pct": "18%-25%",
        "labor_pct": "20%-28%",
        "marketing_pct": "5%-10%",
    },
}
