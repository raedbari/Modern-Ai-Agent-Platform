from fastapi.routing import APIRoute

from backend.app.main import app


def test_api_routes_have_unique_method_path_pairs():
    seen: dict[tuple[str, str], str] = {}
    duplicates: list[dict[str, str]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue

            key = (method, route.path)

            if key in seen:
                duplicates.append(
                    {
                        "method": method,
                        "path": route.path,
                        "first": seen[key],
                        "second": route.name,
                    }
                )
            else:
                seen[key] = route.name

    assert duplicates == [], (
        f"Duplicate API routes detected: {duplicates}"
    )
