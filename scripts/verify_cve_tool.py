"""
Verification script for check_ubuntu_cves().
Run from the repo root with:
    python3 scripts/verify_cve_tool.py
"""
import json
import sys
import os

# Ensure the package is importable from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sysagent.system.tools import check_ubuntu_cves

print("=" * 60)
print("  SysAgent CVE Tool — Verification Run")
print("=" * 60)

result = check_ubuntu_cves()

print(json.dumps(result, indent=2))

print("\n" + "=" * 60)
if "error" in result:
    print(f"  RESULT: TOOL RETURNED AN ERROR")
elif result.get("total_vulnerabilities", 0) == 0:
    print(f"  RESULT: API responded, no active vulnerabilities found.")
else:
    print(f"  RESULT: Found {result['total_vulnerabilities']} active vulnerability(ies).")
print("=" * 60)
