"""
从 CGTeamwork 查询 TLI 项目角色中文名
直接使用 requests 调用 CGTW REST API，不依赖 cgtw2 SDK
"""

import json
import requests
import sys
import os

requests.packages.urllib3.disable_warnings()

CGTW_HOST = "cgt-artstudio.xindong.com"
CGTW_PORT = 8443
ACCOUNT = "wuyixiang@xd.com"
PASSWORD = "ares1121qqwq"

BASE_URL = f"https://{CGTW_HOST}:{CGTW_PORT}"
API_URL = f"{BASE_URL}/api.php"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

session = requests.Session()
session.verify = False


def api_call(controller, method, data=None, token=""):
    payload = {
        "controller": controller,
        "method": method,
        "token": token,
    }
    if data:
        payload.update(data)
    resp = session.post(API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, dict) and result.get("code") == "1":
        raise Exception(f"CGTW API error: {result.get('data', result)}")
    if isinstance(result, dict) and "data" in result:
        return result["data"]
    return result


def login():
    print(f"正在登录 {CGTW_HOST}:{CGTW_PORT} ...")
    data = api_call("account", "login", {
        "account": ACCOUNT,
        "password": PASSWORD,
        "machine_key": "",
    })
    if not isinstance(data, dict) or "token" not in data:
        raise Exception(f"登录失败: {data}")
    print(f"登录成功: {data.get('account', ACCOUNT)}")
    return data["token"]


def get_projects(token):
    print("\n查询所有项目数据库...")
    data = api_call("c_orm", "get_with_filter", {
        "db": "public",
        "module": "project",
        "module_type": "info",
        "sign_array": ["project.entity", "project.database", "project.status", "project.code"],
        "sign_filter_array": [],
        "order_sign_array": [],
        "limit": "200",
        "start_num": "",
    }, token)
    return data


def get_modules(token, db):
    print(f"\n查询 {db} 的模块...")
    data = api_call("info", "modules", {"db": db}, token)
    return data


def get_fields(token, db, module):
    print(f"\n查询 {db}.{module} 的字段...")
    data = api_call("info", "fields_and_str", {"db": db, "module": module}, token)
    return data


def get_assets(token, db, field_list):
    print(f"\n查询 {db} asset 数据...")
    data = api_call("info", "get_filter", {
        "db": db,
        "module": "asset",
        "sign_array": field_list,
        "sign_filter_array": [],
        "order_sign_array": ["asset.entity"],
        "limit": "5000",
        "start_num": "",
    }, token)
    return data


def main():
    token = login()

    # Step 1: 查找 TLI 项目数据库
    projects = get_projects(token)
    if projects:
        print("\n所有项目:")
        tli_db = None
        for p in projects:
            name = p.get("project.entity", "")
            db = p.get("project.database", "")
            code = p.get("project.code", "")
            status = p.get("project.status", "")
            print(f"  {name} | 代号:{code} | 数据库:{db} | 状态:{status}")
            if code and "TLI" in code.upper():
                tli_db = db
            elif name and "TLI" in name.upper():
                tli_db = db
        if tli_db:
            print(f"\n找到 TLI 数据库: {tli_db}")
        else:
            print("\n未找到 TLI 项目，请手动确认数据库名")
            return
    else:
        print("未能获取项目列表，尝试常见数据库名...")
        tli_db = "proj_tli"

    # Step 2: 查看 asset 模块字段
    fields = get_fields(token, tli_db, "asset")
    if fields:
        print(f"\nasset 模块字段 ({len(fields)} 个):")
        for f in fields:
            sign = f.get("sign", "")
            cn = f.get("str", "")
            print(f"  {sign:40s} → {cn}")

    # Step 3: 查询角色数据
    query_fields = ["asset.entity", "asset.cn_name", "asset.asset_name"]
    valid_fields = [qf for qf in query_fields if any(f.get("sign") == qf for f in (fields or []))]
    if not valid_fields:
        valid_fields = ["asset.entity"]
        if fields:
            for f in fields:
                s = f.get("sign", "")
                n = f.get("str", "").lower()
                if "名" in n or "name" in n.lower():
                    valid_fields.append(s)
            valid_fields = list(dict.fromkeys(valid_fields))

    print(f"\n使用字段: {valid_fields}")
    assets = get_assets(token, tli_db, valid_fields)
    if assets:
        print(f"\n角色数据 ({len(assets)} 条):")
        for a in assets:
            print(f"  {json.dumps(a, ensure_ascii=False)}")

        out_path = os.path.join(SCRIPT_DIR, "cgtw-asset-names.json")
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(assets, fp, ensure_ascii=False, indent=2)
        print(f"\n已保存到: {out_path}")
    else:
        print("未查询到资产数据")


if __name__ == "__main__":
    main()
