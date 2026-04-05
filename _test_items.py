import asyncio, httpx


async def test(name):
    url = f"https://steamcommunity.com/market/listings/730/{name}/render"
    async with httpx.AsyncClient(follow_redirects=True) as c:
        r = await c.get(
            url,
            params={"start": "0", "count": "1", "currency": "1", "language": "english"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        print(f"{name}: status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            assets = data.get("assets", {})
            found = False
            for ctx in assets.values():
                for items in ctx.values():
                    for item in items.values():
                        print("  icon_url:", item.get("icon_url", "")[:60])
                        found = True
                        break
            if not found:
                print("  no assets, keys:", list(data.keys()))
        else:
            print("  body:", r.text[:300])


async def main():
    await test("Antwerp 2022 Challengers Sticker Capsule")
    await test("Antwerp 2022 Legends Sticker Capsule")
    # also test via search fallback
    from services.image_proxy import fetch_from_csgodb

    for name in ["Antwerp 2022 Challengers Sticker Capsule", "Antwerp 2022 Legends Sticker Capsule"]:
        result = await fetch_from_csgodb(name)
        print(f"fetch_from_csgodb({name!r}): {'OK ' + str(len(result[0])) + ' bytes' if result else 'None'}")


asyncio.run(main())
