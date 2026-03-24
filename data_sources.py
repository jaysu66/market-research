"""
数据源工具集 — Agent 按需调用的统一接口

所有数据源封装为独立函数，Agent 通过 call_data_source(source_name, params) 调用。
每个函数返回统一格式：
{
    "source": "数据源名称",
    "source_type": "api_precise" | "api_realtime" | "search" | "estimate",
    "data_year": "2024",
    "fetched_at": "2026-03-23T10:00:00",
    "data": { ... },
    "cost": 0.0,
    "error": None
}
"""

import httpx
import json
import os
import time
from datetime import datetime


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _safe_float(v):
    try:
        return float(v) if v and v != "null" else None
    except (ValueError, TypeError):
        return None


# ============================================================
# 第一类：固定调用（步骤1-4，每次必调）
# ============================================================

def census_acs(state_fips: str, fields: list = None) -> dict:
    """Census ACS 5-year — 人口/收入/住房/族裔（州+城市级）
    免费无限，无需Key（有Key更快）。数据年份：2023。
    """
    if fields is None:
        fields = ["NAME", "B01003_001E", "B19013_001E", "B25077_001E",
                  "B25064_001E", "B25001_001E"]

    key = os.environ.get("CENSUS_API_KEY", "")
    key_param = f"&key={key}" if key else ""
    fields_str = ",".join(fields)

    result = {
        "source": "Census ACS 5-year",
        "source_type": "api_precise",
        "data_year": "2023",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {"state_level": None, "cities": []}
    }

    try:
        # 州级
        url = f"https://api.census.gov/data/2023/acs/acs5?get={fields_str}&for=state:{state_fips}{key_param}"
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        rows = resp.json()
        if len(rows) > 1:
            header = rows[0]
            vals = rows[1]
            result["data"]["state_level"] = _parse_census_row(header, vals)

        # 城市级
        url2 = f"https://api.census.gov/data/2023/acs/acs5?get={fields_str}&for=place:*&in=state:{state_fips}{key_param}"
        resp2 = httpx.get(url2, timeout=60, follow_redirects=True)
        resp2.raise_for_status()
        rows2 = resp2.json()
        header2 = rows2[0]
        cities = []
        for r in rows2[1:]:
            parsed = _parse_census_row(header2, r)
            if parsed.get("population") and parsed["population"] > 10000:
                cities.append(parsed)
        cities.sort(key=lambda x: x.get("population", 0), reverse=True)
        result["data"]["cities"] = cities[:20]
    except Exception as e:
        result["error"] = str(e)

    return result


def census_cbp(state_fips: str, naics: str = "442291") -> dict:
    """Census Business Patterns — 行业企业数/员工/薪资（州+县级）
    免费无限，无需Key。数据年份：2022。
    NAICS 442291 = Window Treatment Stores
    """
    result = {
        "source": "Census CBP",
        "source_type": "api_precise",
        "data_year": "2022",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {"state_level": {}, "by_county": []}
    }

    try:
        # 州级
        url = f"https://api.census.gov/data/2022/cbp?get=ESTAB,EMP,PAYANN,NAICS2017_LABEL&for=state:{state_fips}&NAICS2017={naics}"
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
        if len(rows) > 1:
            result["data"]["state_level"] = {
                "establishments": int(rows[1][0] or 0),
                "employees": int(rows[1][1] or 0),
                "annual_payroll_thousands": int(rows[1][2] or 0),
                "industry": rows[1][3],
                "naics": naics,
            }

        # 县级
        url2 = f"https://api.census.gov/data/2022/cbp?get=ESTAB,EMP,PAYANN,NAME&for=county:*&in=state:{state_fips}&NAICS2017={naics}"
        resp2 = httpx.get(url2, timeout=15)
        resp2.raise_for_status()
        rows2 = resp2.json()
        counties = []
        for r in rows2[1:]:
            counties.append({
                "name": r[3],
                "establishments": int(r[0] or 0),
                "employees": int(r[1] or 0),
                "annual_payroll_thousands": int(r[2] or 0),
            })
        counties.sort(key=lambda x: x["establishments"], reverse=True)
        result["data"]["by_county"] = counties
    except Exception as e:
        result["error"] = str(e)

    return result


def census_housing(state_fips: str) -> dict:
    """Census ACS Housing — 自有率/迁入人口/房间数/房龄
    免费无限。数据年份：2023。
    """
    result = {
        "source": "Census ACS Housing",
        "source_type": "api_precise",
        "data_year": "2023",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {}
    }

    try:
        # 住房 tenure
        url = f"https://api.census.gov/data/2023/acs/acs5?get=NAME,B25003_001E,B25003_002E,B25003_003E,B25018_001E,B25035_001E&for=state:{state_fips}"
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        rows = resp.json()
        if len(rows) > 1:
            r = rows[1]
            total = int(r[1] or 0)
            owner = int(r[2] or 0)
            renter = int(r[3] or 0)
            result["data"] = {
                "total_units": total,
                "owner_occupied": owner,
                "renter_occupied": renter,
                "ownership_rate": round(owner / total * 100, 1) if total else 0,
                "median_rooms": _safe_float(r[4]),
                "median_year_built": r[5],
            }

        # 迁入人口
        url2 = f"https://api.census.gov/data/2023/acs/acs5?get=NAME,B07001_001E,B07001_065E,B07001_081E&for=state:{state_fips}"
        resp2 = httpx.get(url2, timeout=30, follow_redirects=True)
        resp2.raise_for_status()
        rows2 = resp2.json()
        if len(rows2) > 1:
            r2 = rows2[1]
            result["data"]["migration"] = {
                "total_population": int(r2[1] or 0),
                "from_different_state": int(r2[2] or 0),
                "from_abroad": int(r2[3] or 0),
            }
    except Exception as e:
        result["error"] = str(e)

    return result


def fred(state_abbr: str) -> dict:
    """FRED — GDP/失业率/建筑许可
    免费120次/分钟，需Key。数据年份：2024。
    """
    api_key = os.environ.get("FRED_API_KEY", "")
    result = {
        "source": "FRED",
        "source_type": "api_precise",
        "data_year": "2024",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {}
    }

    if not api_key:
        result["error"] = "Missing FRED_API_KEY"
        return result

    series_map = {
        "gdp": f"{state_abbr}NGSP",
        "unemployment": f"{state_abbr}UR",
        "building_permits": f"{state_abbr}BPPRIVSA",
    }

    for name, series_id in series_map.items():
        try:
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&sort_order=desc&limit=1"
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            obs = data.get("observations", [])
            if obs:
                result["data"][name] = {
                    "value": _safe_float(obs[0]["value"]),
                    "date": obs[0]["date"],
                    "series_id": series_id,
                }
        except Exception as e:
            result["data"][name] = {"error": str(e)}
        time.sleep(0.2)

    return result


def bls_wages(state_fips: str) -> dict:
    """BLS OEWS — 行业工资（销售岗/建筑岗）
    免费25次/天（v1无Key）。数据年份：2024。
    """
    result = {
        "source": "BLS OEWS",
        "source_type": "api_precise",
        "data_year": "2024",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {}
    }

    area_code = f"{state_fips}00000"
    series_ids = [
        f"OEUS{area_code}00000041000004",  # Sales (SOC 41-0000)
        f"OEUS{area_code}00000047000004",  # Construction (SOC 47-0000)
    ]

    try:
        url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
        body = {"seriesid": series_ids, "startyear": "2024", "endyear": "2024"}
        resp = httpx.post(url, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for series in data.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            series_data = series.get("data", [])
            if series_data:
                latest = series_data[0]
                if "041000" in sid:
                    result["data"]["retail_sales_wage"] = {
                        "value": _safe_float(latest["value"]),
                        "year": latest["year"],
                        "description": "Sales Occupations (SOC 41-0000) annual mean wage",
                    }
                elif "047000" in sid:
                    result["data"]["construction_wage"] = {
                        "value": _safe_float(latest["value"]),
                        "year": latest["year"],
                        "description": "Construction Occupations (SOC 47-0000) annual mean wage",
                    }
    except Exception as e:
        result["error"] = str(e)

    return result


def hud_fmr(state_abbr: str) -> dict:
    """HUD Fair Market Rent — 各都会区住房租金
    免费无限，需Token。数据年份：2026（当年）。
    """
    token = os.environ.get("HUD_API_KEY", "")
    result = {
        "source": "HUD FMR",
        "source_type": "api_precise",
        "data_year": "2026",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {"metroareas": []}
    }

    if not token:
        result["error"] = "Missing HUD_API_KEY"
        return result

    try:
        url = f"https://www.huduser.gov/hudapi/public/fmr/statedata/{state_abbr}"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        metros = data.get("data", {}).get("metroareas", [])
        result["data"]["metroareas"] = metros
        result["data"]["year"] = data.get("data", {}).get("year")
    except Exception as e:
        result["error"] = str(e)

    return result


# ============================================================
# 第二类：Agent 按需调用（步骤9-11，缺什么调什么）
# ============================================================

def google_places(query: str, max_results: int = 10) -> dict:
    """Google Places API — 商家名/地址/评分/评论/营业时间/网站（实时）
    $200/月免费额度，$0.032/次。
    """
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    result = {
        "source": "Google Places",
        "source_type": "api_realtime",
        "data_year": "实时",
        "fetched_at": _now(),
        "cost": 0.032,
        "error": None,
        "data": {"places": []}
    }

    if not api_key:
        result["error"] = "Missing GOOGLE_PLACES_API_KEY"
        return result

    try:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.currentOpeningHours,places.websiteUri,places.priceLevel",
        }
        body = {"textQuery": query, "maxResultCount": min(max_results, 20)}
        resp = httpx.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for p in data.get("places", []):
            place = {
                "name": p.get("displayName", {}).get("text"),
                "address": p.get("formattedAddress"),
                "rating": p.get("rating"),
                "review_count": p.get("userRatingCount"),
                "website": p.get("websiteUri"),
                "price_level": p.get("priceLevel"),
                "hours": p.get("currentOpeningHours", {}).get("weekdayDescriptions", []),
            }
            result["data"]["places"].append(place)
    except Exception as e:
        result["error"] = str(e)

    return result


def rentcast(zip_code: str = None, city: str = None, state: str = None) -> dict:
    """RentCast — 租金数据（实时）
    50次/月免费，超出拒绝请求不扣费。
    """
    api_key = os.environ.get("RENTCAST_API_KEY", "")
    result = {
        "source": "RentCast",
        "source_type": "api_realtime",
        "data_year": "实时",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {}
    }

    if not api_key:
        result["error"] = "Missing RENTCAST_API_KEY"
        return result

    try:
        params = {"dataType": "rental"}
        if zip_code:
            params["zipCode"] = zip_code
        elif city and state:
            params["city"] = city
            params["state"] = state

        resp = httpx.get(
            "https://api.rentcast.io/v1/markets",
            params=params,
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        result["data"] = resp.json()
    except Exception as e:
        result["error"] = str(e)

    return result


def bea_gdp(state_fips: str, table: str = "CAGDP2") -> dict:
    """BEA — GDP按行业细分/个人收入（州级和都会区级）
    免费无限，需Key。数据年份：2023。
    """
    api_key = os.environ.get("BEA_API_KEY", "")
    result = {
        "source": "BEA",
        "source_type": "api_precise",
        "data_year": "2023",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {}
    }

    if not api_key:
        result["error"] = "Missing BEA_API_KEY"
        return result

    try:
        geo_fips = f"{state_fips}000"
        url = f"https://apps.bea.gov/api/data/?UserID={api_key}&method=GetData&DataSetName=Regional&TableName={table}&LineCode=1&GeoFips={geo_fips}&Year=2023&ResultFormat=JSON"
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("BEAAPI", {}).get("Results", {}).get("Data", [])
        result["data"]["records"] = results
    except Exception as e:
        result["error"] = str(e)

    return result


def sec_edgar(company: str) -> dict:
    """SEC EDGAR — 上市公司财报（10-K/10-Q）
    免费10次/秒，无需Key。实时。
    """
    result = {
        "source": "SEC EDGAR",
        "source_type": "api_realtime",
        "data_year": "实时",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {}
    }

    try:
        url = f"https://efts.sec.gov/LATEST/search-index?q={company}&dateRange=custom&startdt=2024-01-01&forms=10-K"
        resp = httpx.get(url, timeout=15, headers={"User-Agent": "MarketResearch/1.0 research@example.com"})
        resp.raise_for_status()
        result["data"] = resp.json()
    except Exception as e:
        result["error"] = str(e)

    return result


def census_building_permits(state_fips: str) -> dict:
    """Census Building Permits Survey — 月度新建住房许可（到县级）
    免费无限，无需Key。数据年份：2025（月度更新）。
    """
    result = {
        "source": "Census Building Permits",
        "source_type": "api_precise",
        "data_year": "2025",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {}
    }

    try:
        url = f"https://api.census.gov/data/2024/cbp?get=ESTAB&for=state:{state_fips}&NAICS2017=236"
        resp = httpx.get(url, timeout=15)
        # 如果CBP没有建筑许可数据，用FRED兜底
        if resp.status_code != 200:
            result["data"]["note"] = "Use FRED building permits data instead"
        else:
            result["data"] = resp.json()
    except Exception as e:
        result["error"] = str(e)

    return result


def chicago_fed_carts() -> dict:
    """Chicago Fed CARTS — 周度零售消费预测（全国级）
    免费无限，无需Key。实时。
    """
    result = {
        "source": "Chicago Fed CARTS",
        "source_type": "api_realtime",
        "data_year": "实时",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {"note": "Download CSV from chicagofed.org/research/data/carts"}
    }
    return result


def data_gov_search(query: str, rows: int = 5) -> dict:
    """Data.gov CKAN — 联邦数据集搜索
    免费无限，无需Key。
    """
    result = {
        "source": "Data.gov",
        "source_type": "api_realtime",
        "data_year": "实时",
        "fetched_at": _now(),
        "cost": 0.0,
        "error": None,
        "data": {"datasets": []}
    }

    try:
        url = f"https://catalog.data.gov/api/3/action/package_search?q={query}&rows={rows}"
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for r in data.get("result", {}).get("results", []):
            result["data"]["datasets"].append({
                "title": r.get("title"),
                "notes": r.get("notes", "")[:200],
                "url": r.get("url"),
            })
    except Exception as e:
        result["error"] = str(e)

    return result


def sonar_search(query: str) -> dict:
    """Perplexity Sonar — 联网搜索
    通过OpenRouter调用，约$0.003/次。实时。
    """
    from model_client import call_sonar

    result = {
        "source": "Perplexity Sonar",
        "source_type": "search",
        "data_year": "实时",
        "fetched_at": _now(),
        "cost": 0.003,
        "error": None,
        "data": {}
    }

    try:
        resp = call_sonar(query)
        result["data"] = {
            "content": resp.get("content", ""),
            "usage": resp.get("usage", {}),
        }
    except Exception as e:
        result["error"] = str(e)

    return result


# ============================================================
# 统一调用接口 — Agent 通过这个函数调用任何数据源
# ============================================================

# 数据源注册表
DATA_SOURCES = {
    # 固定调用（步骤1-4）
    "census_acs": {
        "fn": census_acs,
        "description": "人口/收入/住房数据（州+城市级）",
        "type": "api_precise",
        "year": "2023",
        "cost": 0,
        "params": ["state_fips"],
        "category": "fixed",
    },
    "census_cbp": {
        "fn": census_cbp,
        "description": "行业企业数/员工/薪资（州+县级）",
        "type": "api_precise",
        "year": "2022",
        "cost": 0,
        "params": ["state_fips", "naics"],
        "category": "fixed",
    },
    "census_housing": {
        "fn": census_housing,
        "description": "住房自有率/迁入人口/房间数/房龄",
        "type": "api_precise",
        "year": "2023",
        "cost": 0,
        "params": ["state_fips"],
        "category": "fixed",
    },
    "fred": {
        "fn": fred,
        "description": "GDP/失业率/建筑许可",
        "type": "api_precise",
        "year": "2024",
        "cost": 0,
        "params": ["state_abbr"],
        "category": "fixed",
    },
    "bls_wages": {
        "fn": bls_wages,
        "description": "行业工资（销售岗/建筑岗）",
        "type": "api_precise",
        "year": "2024",
        "cost": 0,
        "params": ["state_fips"],
        "category": "fixed",
    },
    "hud_fmr": {
        "fn": hud_fmr,
        "description": "各都会区住房租金",
        "type": "api_precise",
        "year": "2026",
        "cost": 0,
        "params": ["state_abbr"],
        "category": "fixed",
    },
    "google_places": {
        "fn": google_places,
        "description": "商家名/地址/评分/评论/营业时间/网站（实时）",
        "type": "api_realtime",
        "year": "实时",
        "cost": 0.032,
        "params": ["query", "max_results"],
        "category": "fixed",
    },
    # Agent 按需调用
    "rentcast": {
        "fn": rentcast,
        "description": "真实租金数据（实时，按ZIP或城市）",
        "type": "api_realtime",
        "year": "实时",
        "cost": 0,
        "params": ["zip_code", "city", "state"],
        "category": "on_demand",
        "limit": "50次/月",
    },
    "bea_gdp": {
        "fn": bea_gdp,
        "description": "GDP按行业细分/个人收入",
        "type": "api_precise",
        "year": "2023",
        "cost": 0,
        "params": ["state_fips", "table"],
        "category": "on_demand",
    },
    "sec_edgar": {
        "fn": sec_edgar,
        "description": "上市公司财报搜索",
        "type": "api_realtime",
        "year": "实时",
        "cost": 0,
        "params": ["company"],
        "category": "on_demand",
    },
    "census_building_permits": {
        "fn": census_building_permits,
        "description": "月度新建住房许可（县级）",
        "type": "api_precise",
        "year": "2025",
        "cost": 0,
        "params": ["state_fips"],
        "category": "on_demand",
    },
    "chicago_fed_carts": {
        "fn": chicago_fed_carts,
        "description": "周度零售消费预测（全国级）",
        "type": "api_realtime",
        "year": "实时",
        "cost": 0,
        "params": [],
        "category": "on_demand",
    },
    "data_gov": {
        "fn": data_gov_search,
        "description": "联邦数据集搜索",
        "type": "api_realtime",
        "year": "实时",
        "cost": 0,
        "params": ["query", "rows"],
        "category": "on_demand",
    },
    "sonar_search": {
        "fn": sonar_search,
        "description": "Perplexity联网搜索",
        "type": "search",
        "year": "实时",
        "cost": 0.003,
        "params": ["query"],
        "category": "on_demand",
    },
}


def call_data_source(source_name: str, **params) -> dict:
    """统一调用接口 — Agent 通过这个函数调用任何数据源

    Args:
        source_name: 数据源名称（如 "census_acs", "google_places"）
        **params: 该数据源需要的参数

    Returns:
        统一格式的结果字典
    """
    if source_name not in DATA_SOURCES:
        return {
            "source": source_name,
            "error": f"Unknown data source: {source_name}. Available: {list(DATA_SOURCES.keys())}",
        }

    source = DATA_SOURCES[source_name]
    fn = source["fn"]

    try:
        return fn(**params)
    except Exception as e:
        return {
            "source": source_name,
            "error": str(e),
            "fetched_at": _now(),
        }


def list_data_sources(category: str = None) -> list:
    """列出所有可用数据源

    Args:
        category: "fixed" | "on_demand" | None(全部)
    """
    sources = []
    for name, info in DATA_SOURCES.items():
        if category and info["category"] != category:
            continue
        sources.append({
            "name": name,
            "description": info["description"],
            "type": info["type"],
            "year": info["year"],
            "cost": info["cost"],
            "category": info["category"],
            "params": info["params"],
            "limit": info.get("limit"),
        })
    return sources


# ============================================================
# 辅助函数
# ============================================================

def _parse_census_row(header: list, values: list) -> dict:
    """解析 Census API 返回的一行数据"""
    result = {}
    field_map = {
        "NAME": "name",
        "B01003_001E": "population",
        "B19013_001E": "median_income",
        "B25077_001E": "median_home_value",
        "B25064_001E": "median_rent",
        "B25001_001E": "housing_units",
    }

    for i, col in enumerate(header):
        if col in field_map:
            key = field_map[col]
            val = values[i]
            if key == "name":
                result[key] = val
            else:
                result[key] = int(val) if val and val != "null" else None
        elif col == "state":
            result["state_fips"] = values[i]
        elif col == "place":
            result["place_fips"] = values[i]

    return result


if __name__ == "__main__":
    """测试所有数据源"""
    print("=== Available Data Sources ===")
    for s in list_data_sources():
        limit = f" (limit: {s['limit']})" if s.get("limit") else ""
        print(f"  [{s['category']}] {s['name']}: {s['description']} — {s['type']} {s['year']} ${s['cost']}{limit}")

    print(f"\nTotal: {len(DATA_SOURCES)} sources")
    print(f"  Fixed: {len([s for s in DATA_SOURCES.values() if s['category']=='fixed'])}")
    print(f"  On-demand: {len([s for s in DATA_SOURCES.values() if s['category']=='on_demand'])}")
