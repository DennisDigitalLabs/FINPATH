from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = [
    *sorted((ROOT / "frontend").glob("*.html")),
    ROOT / "frontend/js/api.js",
    ROOT / "frontend/js/assessment.js",
    ROOT / "frontend/js/dashboard.js",
    ROOT / "frontend/js/prediction.js",
    ROOT / "frontend/js/recommendations.js",
    ROOT / "frontend/js/analytics.js",
    ROOT / "frontend/js/admin.js",
]
PROTECTED_IDENTIFIERS = (
    "FINPATH_CONFIG",
    "FinpathAPI",
    "FinpathApiError",
    "FinpathNetworkError",
    "FinpathPredictor",
    "RealFinpathPredictor",
    "finpath_access_token",
    "finpath_api_base_url",
)


def public_text(path):
    text = path.read_text(encoding="utf-8")
    for identifier in PROTECTED_IDENTIFIERS:
        text = text.replace(identifier, "")
    return text


def test_public_frontend_contains_no_project_branding():
    forbidden = "finpath"
    violations = {
        str(path.relative_to(ROOT)): [
            (line_number, line)
            for line_number, line in enumerate(public_text(path).splitlines(), start=1)
            if forbidden in line.lower()
        ]
        for path in PUBLIC_FILES
    }
    violations = {path: matches for path, matches in violations.items() if matches}
    assert not violations, violations