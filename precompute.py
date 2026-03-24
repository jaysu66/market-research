"""步骤1-4：预计算 — 一次性拉取 Census/FRED/BLS/Overpass(OSM) 数据"""

import httpx
import json
import os
import time
from pathlib import Path

from config import US_STATES, PRODUCTS, FRED_SERIES, STATE_ABBR_MAP

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


# ========== 步骤1：Census API ==========

def fetch_census(api_key: str, state_fips: str | None = None) -> list[dict]:
    """
    拉取 Census ACS 5-year 数据
    state_fips=None 时拉全美所有州的所有城市
    """
    fields = ",".join([
        "NAME",
        "B01003_001E",  # 总人口
        "B19013_001E",  # 家庭收入中位数
        "B25077_001E",  # 自有住房中位价值
        "B25064_001E",  # 租金中位数
        "B25001_001E",  # 住房单元总数
    ])

    results = []

    # Census API 不带Key也能用，带了反而可能invalid_key
    # 不带Key限流50次/IP/天，够用
    if state_fips:
        # 单州: 拿该州所有城市
        url = f"https://api.census.gov/data/2023/acs/acs5?get={fields}&for=place:*&in=state:{state_fips}"
        resp = httpx.get(url, timeout=60)
        if resp.status_code == 200 and resp.text.startswith("["):
            results = _parse_census(resp.json())
        else:
            print(f"  Census place data failed: {resp.status_code}")
            results = []

        # 也拿州级汇总
        url_state = f"https://api.census.gov/data/2023/acs/acs5?get={fields}&for=state:{state_fips}"
        resp2 = httpx.get(url_state, timeout=30)
        if resp2.status_code == 200 and resp2.text.startswith("["):
            state_data = _parse_census(resp2.json())
            results = state_data + results
    else:
        # 全美: 先拿所有州汇总
        url_states = f"https://api.census.gov/data/2023/acs/acs5?get={fields}&for=state:*"
        resp = httpx.get(url_states, timeout=30)
        if resp.status_code == 200 and resp.text.startswith("["):
            results = _parse_census(resp.json())

    return results


def _parse_census(raw: list) -> list[dict]:
    """解析 Census API 返回的二维数组"""
    if not raw or len(raw) < 2:
        return []
    headers = raw[0]
    parsed = []
    for row in raw[1:]:
        entry = {}
        for i, h in enumerate(headers):
            val = row[i]
            if h == "NAME":
                entry["name"] = val
            elif h == "B01003_001E":
                entry["population"] = _safe_int(val)
            elif h == "B19013_001E":
                entry["median_income"] = _safe_int(val)
            elif h == "B25077_001E":
                entry["median_home_value"] = _safe_int(val)
            elif h == "B25064_001E":
                entry["median_rent"] = _safe_int(val)
            elif h == "B25001_001E":
                entry["housing_units"] = _safe_int(val)
            elif h == "state":
                entry["state_fips"] = val
            elif h == "place":
                entry["place_fips"] = val
        entry["source"] = "Census ACS 2023 5-year"
        parsed.append(entry)
    return parsed


def _safe_int(val) -> int | None:
    """安全转换整数，Census用负数表示无数据"""
    try:
        v = int(val)
        return v if v >= 0 else None
    except (ValueError, TypeError):
        return None


# ========== 步骤2：FRED API ==========

def fetch_fred(api_key: str, state_abbr: str) -> dict:
    """拉取单州的 GDP/失业率/建筑许可"""
    result = {"state": state_abbr, "source": "FRED / BEA"}

    for metric, template in FRED_SERIES.items():
        series_id = template.replace("XX", state_abbr)
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={api_key}"
            f"&sort_order=desc&limit=5&file_type=json"
        )
        try:
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            obs = data.get("observations", [])
            if obs:
                latest = obs[0]
                result[metric] = {
                    "value": _safe_float(latest["value"]),
                    "date": latest["date"],
                    "series_id": series_id,
                }
        except Exception as e:
            result[metric] = {"value": None, "error": str(e)}
        time.sleep(0.2)  # 避免限流

    return result


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return v if v != -999999 else None
    except (ValueError, TypeError):
        return None


# ========== 步骤3：BLS API ==========

def fetch_bls(api_key: str, state_fips: str) -> dict:
    """拉取单州的零售业/建筑业平均工资"""
    # OEWS series: OEUSXXXXXXXX000000001103
    # 格式: OEU + S + area_code + 000000 + industry_code + data_type
    # 41-0000: Retail Sales Workers
    # 47-0000: Construction Workers

    result = {"state_fips": state_fips, "source": "BLS OEWS"}

    # 正确的25位Series ID格式:
    # OE + U + S + area_code(7位) + industry(6位) + occupation(6位) + datatype(2位)
    # area_code: FIPS州码 + 00000 (如德州48 → 4800000)
    # industry: 000000 (跨行业)
    # occupation: 041000 (Sales 41-0000) / 047000 (Construction 47-0000)
    # datatype: 04 (annual mean wage)
    # area_code = 7位: FIPS州码(2位) + 00000(5位)
    # industry = 6位: 000000 (跨行业)
    # occupation = 6位: 041000 / 047000
    # datatype = 2位: 04 (annual mean wage)
    # 总长: OE(2) + U(1) + S(1) + area(7) + industry(6) + occupation(6) + datatype(2) = 25
    area_code = f"{state_fips}00000"  # 7位
    series_ids = [
        f"OEUS{area_code}00000041000004",  # Sales workers (SOC 41-0000), annual mean wage
        f"OEUS{area_code}00000047000004",  # Construction workers (SOC 47-0000), annual mean wage
    ]

    # 用v1（无需Key，每天25次限制，50州够用）
    # v2 Key经常过期，v1更稳定
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    body = {
        "seriesid": series_ids,
        "startyear": "2024",
        "endyear": "2024",
    }

    try:
        resp = httpx.post(url, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for series in data.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            series_data = series.get("data", [])
            if series_data:
                latest = series_data[0]
                if "041000" in sid:
                    result["retail_sales_wage"] = {
                        "value": _safe_float(latest["value"]),
                        "year": latest["year"],
                        "period": latest["period"],
                        "description": "Sales and Related Occupations (SOC 41-0000) annual mean wage",
                    }
                elif "047000" in sid:
                    result["construction_wage"] = {
                        "value": _safe_float(latest["value"]),
                        "year": latest["year"],
                        "period": latest["period"],
                        "description": "Construction and Extraction Occupations (SOC 47-0000) annual mean wage",
                    }
    except Exception as e:
        result["error"] = str(e)

    return result


# ========== 步骤3b：Census Business Patterns API ==========

# NAICS codes for home furnishing related industries
CBP_NAICS = {
    "curtains": {
        "442291": "Window treatment stores",
        "442299": "All other home furnishings stores",
        "238390": "Other building finishing contractors",
    },
    "carpet": {
        "442210": "Floor covering stores",
        "442299": "All other home furnishings stores",
        "238330": "Flooring contractors",
    },
}


def fetch_cbp(state_fips: str, product: str = "curtains") -> dict:
    """拉取 Census Business Patterns — 行业企业数量、员工数、薪资"""
    naics_codes = CBP_NAICS.get(product, CBP_NAICS["curtains"])
    result = {"source": "Census Business Patterns 2022", "industries": {}}

    for naics, label in naics_codes.items():
        # 州级汇总
        try:
            url = f"https://api.census.gov/data/2022/cbp?get=ESTAB,EMP,PAYANN,NAICS2017_LABEL&for=state:{state_fips}&NAICS2017={naics}"
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            if len(data) > 1:
                row = data[1]
                result["industries"][naics] = {
                    "label": row[3] or label,
                    "establishments": _safe_int(row[0]),
                    "employees": _safe_int(row[1]),
                    "annual_payroll_thousands": _safe_int(row[2]),
                }
        except Exception:
            pass

        # 按县拆分（只查主要行业）
        if naics == list(naics_codes.keys())[0]:  # 只查第一个NAICS的县级数据
            try:
                url_county = f"https://api.census.gov/data/2022/cbp?get=ESTAB,EMP,PAYANN,NAME&for=county:*&in=state:{state_fips}&NAICS2017={naics}"
                resp2 = httpx.get(url_county, timeout=15, follow_redirects=True)
                resp2.raise_for_status()
                data2 = resp2.json()
                counties = []
                for row in data2[1:]:
                    estab = _safe_int(row[0])
                    if estab and estab > 0:
                        counties.append({
                            "county": row[3],
                            "establishments": estab,
                            "employees": _safe_int(row[1]),
                            "annual_payroll_thousands": _safe_int(row[2]),
                        })
                counties.sort(key=lambda x: x["establishments"], reverse=True)
                result["by_county"] = counties[:15]
            except Exception:
                pass

    return result


def fetch_housing_tenure(state_fips: str) -> dict:
    """拉取 Census ACS 住房权属数据（自有vs租住）"""
    try:
        url = f"https://api.census.gov/data/2023/acs/acs5?get=NAME,B25003_001E,B25003_002E,B25003_003E,B25018_001E,B25035_001E&for=state:{state_fips}"
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        row = data[1]
        total = _safe_int(row[1])
        owner = _safe_int(row[2])
        renter = _safe_int(row[3])
        return {
            "total_housing_units_occupied": total,
            "owner_occupied": owner,
            "renter_occupied": renter,
            "owner_rate": round(owner / total * 100, 1) if total else 0,
            "median_rooms": _safe_float(row[4]),
            "median_year_built": _safe_int(row[5]),
            "source": "Census ACS 2023 5-year",
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_migration(state_fips: str) -> dict:
    """拉取 Census ACS 人口流动数据"""
    try:
        url = f"https://api.census.gov/data/2023/acs/acs5?get=NAME,B07001_001E,B07001_065E,B07001_081E&for=state:{state_fips}"
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        row = data[1]
        total = _safe_int(row[1])
        from_other_state = _safe_int(row[2])
        from_abroad = _safe_int(row[3])
        return {
            "total_population_mobility": total,
            "moved_from_other_state": from_other_state,
            "moved_from_abroad": from_abroad,
            "net_inflow_rate": round((from_other_state + from_abroad) / total * 100, 1) if total else 0,
            "source": "Census ACS 2023 5-year",
        }
    except Exception as e:
        return {"error": str(e)}


def _safe_int(val) -> int:
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


# ========== 步骤3d：HUD Fair Market Rent API ==========

def fetch_hud_fmr(api_token: str, state_code: str) -> dict:
    """拉取 HUD 公平市场租金数据"""
    try:
        url = f"https://www.huduser.gov/hudapi/public/fmr/statedata/{state_code}"
        headers = {"Authorization": f"Bearer {api_token}"}
        resp = httpx.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        metros = data.get("data", {}).get("metroareas", [])
        year = data.get("data", {}).get("year", "")

        result = {
            "year": year,
            "source": f"HUD Fair Market Rent {year}",
            "metros": [],
        }

        for m in metros:
            result["metros"].append({
                "name": m.get("metro_name", ""),
                "studio": m.get("Efficiency"),
                "one_br": m.get("One-Bedroom"),
                "two_br": m.get("Two-Bedroom"),
                "three_br": m.get("Three-Bedroom"),
                "four_br": m.get("Four-Bedroom"),
            })

        # 按2BR租金排序
        result["metros"].sort(key=lambda x: x.get("two_br") or 0, reverse=True)
        return result
    except Exception as e:
        return {"error": str(e)}


# ========== 步骤4a：Google Places API ==========

def fetch_google_places(api_key: str, city: str, state: str, product: str) -> list[dict]:
    """用Google Places API搜索商家（实时数据，评分+评论+营业时间）"""
    query_terms = {
        "curtains": "window treatment curtain blinds stores",
        "carpet": "carpet flooring stores",
    }
    query = f'{query_terms.get(product, product)} in {city}, {state}'

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.currentOpeningHours,places.websiteUri,places.priceLevel",
    }
    body = {"textQuery": query, "maxResultCount": 10}

    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        businesses = []
        for p in data.get("places", []):
            hours = p.get("currentOpeningHours", {}).get("weekdayDescriptions", [])
            biz = {
                "name": p.get("displayName", {}).get("text", ""),
                "address": p.get("formattedAddress", ""),
                "city": city,
                "rating": p.get("rating", 0),
                "review_count": p.get("userRatingCount", 0),
                "website": p.get("websiteUri", ""),
                "price_level": p.get("priceLevel", ""),
                "hours": hours[:3] if hours else [],  # 只保留前3天
                "source": "Google Places API (实时)",
            }
            businesses.append(biz)
        return businesses
    except Exception as e:
        return [{"error": str(e), "city": city}]


# ========== 步骤4b：RentCast API ==========

def fetch_rentcast(api_key: str, city: str, state_code: str) -> dict:
    """用RentCast API获取实时租金数据"""
    url = "https://api.rentcast.io/v1/markets"
    params = {"city": city, "state": state_code, "dataType": "rental"}
    headers = {"X-Api-Key": api_key, "Accept": "application/json"}

    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict) and "rentalData" in data:
            rd = data["rentalData"]
            return {
                "city": city,
                "average_rent": rd.get("averageRent"),
                "median_rent": rd.get("medianRent"),
                "avg_per_sqft": rd.get("averageRentPerSquareFoot"),
                "total_listings": rd.get("totalListings"),
                "last_updated": rd.get("lastUpdatedDate", ""),
                "source": "RentCast API (实时)",
            }
        return {"city": city, "no_data": True}
    except Exception as e:
        return {"city": city, "error": str(e)}


# ========== 主函数 ==========

def precompute_state(state_code: str, product: str = "curtains") -> dict:
    """预计算单州所有API数据"""
    state_info = US_STATES[state_code]
    state_name = state_info["name"]
    state_fips = state_info["fips"]
    cities = state_info["cities"]

    census_key = os.environ.get("CENSUS_API_KEY", "")
    fred_key = os.environ.get("FRED_API_KEY", "")
    bls_key = os.environ.get("BLS_API_KEY", "")

    print(f"[1/4] Census API — {state_name}...")
    census_data = fetch_census(census_key, state_fips)  # Key可选，不带也能调
    # 只保留人口>10000的城市，避免太多小城镇
    census_cities = [c for c in census_data if c.get("place_fips") and c.get("population") and c["population"] > 10000]
    census_cities.sort(key=lambda x: x.get("population") or 0, reverse=True)
    census_state = [c for c in census_data if "place_fips" not in c]

    print(f"[2/4] FRED API — {state_name}...")
    fred_data = fetch_fred(fred_key, state_code) if fred_key else {}

    print(f"[3/6] BLS API — {state_name}...")
    bls_data = fetch_bls(bls_key, state_fips) if bls_key else {}

    print(f"[4/6] Census Business Patterns — {state_name} ({product})...")
    cbp_data = fetch_cbp(state_fips, product)

    print(f"[5/7] Census Housing & Migration — {state_name}...")
    housing_data = fetch_housing_tenure(state_fips)
    migration_data = fetch_migration(state_fips)

    hud_key = os.environ.get("HUD_API_KEY", "")
    print(f"[6/7] HUD Fair Market Rent — {state_name}...")
    hud_data = fetch_hud_fmr(hud_key, state_code) if hud_key else {}

    # Google Places（实时商家数据）
    gp_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    print(f"[7/9] Google Places API — {state_name} ({product})...")
    gp_data = {}
    if gp_key:
        for city in cities[:3]:  # 前3个主要城市，控制API用量
            gp_data[city] = fetch_google_places(gp_key, city, state_name, product)
            time.sleep(0.5)
    else:
        print("  [SKIP] GOOGLE_PLACES_API_KEY not set")

    # RentCast（实时租金数据）
    rc_key = os.environ.get("RENTCAST_API_KEY", "")
    print(f"[8/9] RentCast API — {state_name}...")
    rc_data = {}
    if rc_key:
        # 只查第一个主要城市的租金（控制50次/月额度）
        rc_data = fetch_rentcast(rc_key, cities[0], state_code)
    else:
        print("  [SKIP] RENTCAST_API_KEY not set")

    print(f"[9/9] 组装数据池...")

    # 组装数据池
    data_pool = {
        "state": state_code,
        "state_name": state_name,
        "product": product,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "demographics": {
            "state_level": census_state,
            "cities": census_cities[:20],
            "source": "Census ACS 2023 5-year",
        },
        "economy": fred_data,
        "wages": bls_data,
        "industry_stats": cbp_data,
        "housing": housing_data,
        "migration": migration_data,
        "fair_market_rent": hud_data,
        "local_businesses": gp_data,
        "rentcast": rc_data,
    }

    # 保存缓存
    output_dir = CACHE_DIR / f"{state_code}_{product}"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "api_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_pool, f, ensure_ascii=False, indent=2)

    print(f"[OK] 数据已保存: {output_path}")
    return data_pool


def precompute_all_census(api_key: str) -> dict:
    """一次性拉全美所有州所有城市的Census数据"""
    print("拉取全美Census数据（一次调用）...")
    fields = ",".join([
        "NAME", "B01003_001E", "B19013_001E", "B25077_001E", "B25064_001E", "B25001_001E",
    ])

    all_data = {}

    key_param = f"&key={api_key}" if api_key else ""

    # 州级汇总
    url_states = f"https://api.census.gov/data/2023/acs/acs5?get={fields}&for=state:*{key_param}"
    resp = httpx.get(url_states, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    states = _parse_census(resp.json())
    for s in states:
        fips = s.get("state_fips", "")
        all_data[fips] = {"state_level": s, "cities": []}

    # 所有城市（一次调用）
    url_places = f"https://api.census.gov/data/2023/acs/acs5?get={fields}&for=place:*&in=state:*{key_param}"
    print("请求全美城市数据（可能需要10-20秒）...")
    resp2 = httpx.get(url_places, timeout=120, follow_redirects=True)
    resp2.raise_for_status()
    places = _parse_census(resp2.json())

    for p in places:
        fips = p.get("state_fips", "")
        if fips in all_data and p.get("population") and p["population"] > 10000:
            all_data[fips]["cities"].append(p)

    # 按人口排序
    for fips in all_data:
        all_data[fips]["cities"].sort(key=lambda x: x.get("population") or 0, reverse=True)

    output_path = CACHE_DIR / "census_all.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    total_cities = sum(len(v["cities"]) for v in all_data.values())
    print(f"[OK] Census全美数据已保存: {output_path}")
    print(f"   {len(all_data)}个州，{total_cities}个城市（人口>1万）")
    return all_data


# ========== CLI 入口 ==========

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python precompute.py census_all      # 一次拉全美Census")
        print("  python precompute.py TX               # 预计算德州所有API")
        print("  python precompute.py TX carpet         # 预计算德州地毯品类")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "census_all":
        key = os.environ.get("CENSUS_API_KEY", "")
        if not key:
            print("[ERROR] 请设置环境变量 CENSUS_API_KEY")
            sys.exit(1)
        precompute_all_census(key)
    else:
        state = cmd.upper()
        product = sys.argv[2] if len(sys.argv) > 2 else "curtains"
        if state not in US_STATES:
            print(f"[ERROR] 未知州代码: {state}")
            sys.exit(1)
        precompute_state(state, product)
