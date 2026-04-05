"""Debug script to test One2Track login flow step by step."""

import asyncio
import re
import sys

import aiohttp

BASE_URL = "https://www.one2trackgps.com"
LOGIN_PATH = "/auth/users/sign_in"
CSRF_RE = re.compile(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', re.IGNORECASE)
ACCOUNT_ID_RE = re.compile(r"/users/(\d+)")


async def debug_login(email: str, password: str) -> None:
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:

        # Step 1: GET login page
        print(f"[1] GET {BASE_URL}{LOGIN_PATH}")
        async with session.get(f"{BASE_URL}{LOGIN_PATH}", allow_redirects=True) as resp:
            print(f"    Status: {resp.status}")
            print(f"    URL after redirects: {resp.url}")
            print(f"    Content-Type: {resp.headers.get('Content-Type')}")
            html = await resp.text()
            print(f"    HTML length: {len(html)}")

            # Show cookies
            for cookie in jar:
                print(f"    Cookie: {cookie.key}={cookie.value[:20]}...")

            # Find CSRF token
            match = CSRF_RE.search(html)
            if match:
                csrf = match.group(1)
                print(f"    CSRF token: {csrf[:30]}...")
            else:
                print("    ERROR: No CSRF token found!")
                # Print the first 2000 chars to see what we got
                print(f"    HTML preview:\n{html[:2000]}")
                return

        # Step 2: POST credentials
        form_data = {
            "authenticity_token": csrf,
            "user[login]": email,
            "user[password]": password,
            "user[remember_me]": "1",
            "gdpr": "1",
        }

        print(f"\n[2] POST {BASE_URL}{LOGIN_PATH}")
        print(f"    Form fields: {list(form_data.keys())}")
        async with session.post(
            f"{BASE_URL}{LOGIN_PATH}",
            data=form_data,
            allow_redirects=False,
        ) as resp:
            print(f"    Status: {resp.status}")
            location = resp.headers.get("Location", "")
            print(f"    Location header: {location}")
            print(f"    All response headers:")
            for k, v in resp.headers.items():
                print(f"      {k}: {v}")

            # Show cookies after POST
            print(f"    Cookies after POST:")
            for cookie in jar:
                print(f"      {cookie.key}={cookie.value[:30]}...")

            if resp.status not in (301, 302):
                body = await resp.text()
                print(f"    Response body (first 2000 chars):\n{body[:2000]}")
                return

        # Step 3: Follow redirect
        follow_url = location if location.startswith("http") else f"{BASE_URL}{location}"
        print(f"\n[3] GET {follow_url} (follow redirect)")
        async with session.get(follow_url, allow_redirects=True) as resp:
            print(f"    Status: {resp.status}")
            print(f"    Final URL: {resp.url}")

            account_match = ACCOUNT_ID_RE.search(str(resp.url))
            if account_match:
                print(f"    Account ID: {account_match.group(1)}")
            else:
                # Try from location header
                account_match = ACCOUNT_ID_RE.search(location)
                if account_match:
                    print(f"    Account ID (from redirect): {account_match.group(1)}")
                else:
                    print("    ERROR: Could not find account ID")
                    body = await resp.text()
                    print(f"    Body preview:\n{body[:2000]}")

            print(f"    Final cookies:")
            for cookie in jar:
                print(f"      {cookie.key}={cookie.value[:30]}...")

        # Step 4: Try fetching devices
        if account_match:
            account_id = account_match.group(1)
            print(f"\n[4] GET /users/{account_id}/devices (JSON)")
            async with session.get(
                f"{BASE_URL}/users/{account_id}/devices",
                headers={"Accept": "application/json"},
                allow_redirects=True,
            ) as resp:
                print(f"    Status: {resp.status}")
                print(f"    Content-Type: {resp.headers.get('Content-Type')}")
                print(f"    Final URL: {resp.url}")
                body = await resp.text()
                # Truncate if very long
                if len(body) > 3000:
                    print(f"    Body (first 3000 chars):\n{body[:3000]}")
                else:
                    print(f"    Body:\n{body}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <email> <password>")
        sys.exit(1)

    asyncio.run(debug_login(sys.argv[1], sys.argv[2]))
