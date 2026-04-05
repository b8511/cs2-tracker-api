"""
One-time script to seed Cloudflare R2 with all CS2 item images.

Usage:
    Copy .env.example to .env and fill in R2 credentials, then:
    python scripts/seed_images.py

The script fetches each image from csgodatabase.com and uploads it to R2.
Already-uploaded images are skipped (--force to re-upload all).
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv
from services.image_proxy import normalize_name
from services import r2_storage

load_dotenv()

CSGO_DB_BASE = "https://www.csgodatabase.com/images/containers/webp"

# All items from the frontend cs2Items.ts
ALL_ITEMS = [
    "Clutch Case",
    "Prisma Case",
    "Prisma 2 Case",
    "Danger Zone Case",
    "CS:GO Weapon Case",
    "CS:GO Weapon Case 2",
    "CS:GO Weapon Case 3",
    "eSports 2013 Case",
    "eSports 2013 Winter Case",
    "eSports 2014 Summer Case",
    "Operation Bravo Case",
    "Operation Phoenix Case",
    "Operation Breakout Weapon Case",
    "Operation Vanguard Weapon Case",
    "Operation Wildfire Case",
    "Operation Hydra Case",
    "Operation Riptide Case",
    "Huntsman Weapon Case",
    "Falchion Case",
    "Shadow Case",
    "Revolver Case",
    "Chroma Case",
    "Chroma 2 Case",
    "Chroma 3 Case",
    "Gamma Case",
    "Gamma 2 Case",
    "Glove Case",
    "Spectrum Case",
    "Spectrum 2 Case",
    "Fracture Case",
    "Snakebite Case",
    "Dreams & Nightmares Case",
    "Recoil Case",
    "Revolution Case",
    "Kilowatt Case",
    "Gallery Case",
    "Horizon Case",
    "CS20 Case",
    "Shattered Web Case",
    "Broken Fang Case",
    "Fever Case",
    "Copenhagen 2024 Mirage Souvenir Package",
    "Copenhagen 2024 Inferno Souvenir Package",
    "Copenhagen 2024 Nuke Souvenir Package",
    "Copenhagen 2024 Ancient Souvenir Package",
    "Copenhagen 2024 Anubis Souvenir Package",
    "Copenhagen 2024 Vertigo Souvenir Package",
    "Paris 2023 Mirage Souvenir Package",
    "Paris 2023 Inferno Souvenir Package",
    "Paris 2023 Nuke Souvenir Package",
    "Paris 2023 Ancient Souvenir Package",
    "Paris 2023 Anubis Souvenir Package",
    "Paris 2023 Vertigo Souvenir Package",
    "Rio 2022 Mirage Souvenir Package",
    "Rio 2022 Inferno Souvenir Package",
    "Rio 2022 Nuke Souvenir Package",
    "Rio 2022 Overpass Souvenir Package",
    "Rio 2022 Ancient Souvenir Package",
    "Rio 2022 Vertigo Souvenir Package",
    "Antwerp 2022 Mirage Souvenir Package",
    "Antwerp 2022 Inferno Souvenir Package",
    "Antwerp 2022 Nuke Souvenir Package",
    "Antwerp 2022 Overpass Souvenir Package",
    "Antwerp 2022 Ancient Souvenir Package",
    "Antwerp 2022 Vertigo Souvenir Package",
    "Stockholm 2021 Mirage Souvenir Package",
    "Stockholm 2021 Inferno Souvenir Package",
    "Stockholm 2021 Nuke Souvenir Package",
    "Stockholm 2021 Overpass Souvenir Package",
    "Stockholm 2021 Ancient Souvenir Package",
    "Stockholm 2021 Vertigo Souvenir Package",
    "AK-47 | Redline (Field-Tested)",
    "AK-47 | Redline (Minimal Wear)",
    "AK-47 | Asiimov (Field-Tested)",
    "AK-47 | Asiimov (Battle-Scarred)",
    "AK-47 | Vulcan (Factory New)",
    "AK-47 | Vulcan (Minimal Wear)",
    "AK-47 | Vulcan (Field-Tested)",
    "AK-47 | Case Hardened (Factory New)",
    "AK-47 | Case Hardened (Minimal Wear)",
    "AK-47 | Case Hardened (Field-Tested)",
    "AK-47 | Case Hardened (Well-Worn)",
    "AK-47 | Case Hardened (Battle-Scarred)",
    "AK-47 | Fire Serpent (Factory New)",
    "AK-47 | Fire Serpent (Minimal Wear)",
    "AK-47 | Fire Serpent (Field-Tested)",
    "AK-47 | Neon Rider (Factory New)",
    "AK-47 | Neon Rider (Minimal Wear)",
    "AK-47 | Bloodsport (Factory New)",
    "AK-47 | Bloodsport (Minimal Wear)",
    "AK-47 | The Empress (Factory New)",
    "AK-47 | The Empress (Minimal Wear)",
    "AK-47 | The Empress (Field-Tested)",
    "AK-47 | Phantom Disruptor (Factory New)",
    "AK-47 | Ice Coaled (Factory New)",
    "AK-47 | Slate (Factory New)",
    "AK-47 | Slate (Minimal Wear)",
    "AK-47 | Hydroponic (Factory New)",
    "AK-47 | Hydroponic (Minimal Wear)",
    "AK-47 | Wild Lotus (Factory New)",
    "AK-47 | Wild Lotus (Minimal Wear)",
    "AK-47 | Gold Arabesque (Factory New)",
    "AK-47 | Nightwish (Factory New)",
    "AK-47 | Legion of Anubis (Factory New)",
    "AWP | Asiimov (Factory New)",
    "AWP | Asiimov (Minimal Wear)",
    "AWP | Asiimov (Field-Tested)",
    "AWP | Asiimov (Battle-Scarred)",
    "AWP | Dragon Lore (Factory New)",
    "AWP | Dragon Lore (Minimal Wear)",
    "AWP | Dragon Lore (Field-Tested)",
    "AWP | Dragon Lore (Battle-Scarred)",
    "AWP | Lightning Strike (Factory New)",
    "AWP | Hyper Beast (Factory New)",
    "AWP | Hyper Beast (Minimal Wear)",
    "AWP | Hyper Beast (Field-Tested)",
    "AWP | Medusa (Factory New)",
    "AWP | Medusa (Minimal Wear)",
    "AWP | Medusa (Field-Tested)",
    "AWP | Gungnir (Factory New)",
    "AWP | Gungnir (Minimal Wear)",
    "AWP | Containment Breach (Factory New)",
    "AWP | Containment Breach (Minimal Wear)",
    "AWP | Chromatic Aberration (Factory New)",
    "AWP | Chromatic Aberration (Minimal Wear)",
    "AWP | Neo-Noir (Factory New)",
    "AWP | Neo-Noir (Minimal Wear)",
    "AWP | Wildfire (Factory New)",
    "AWP | Wildfire (Minimal Wear)",
    "AWP | Fever Dream (Factory New)",
    "AWP | The Prince (Factory New)",
    "AWP | Graphite (Factory New)",
    "AWP | BOOM (Factory New)",
    "AWP | BOOM (Minimal Wear)",
    "M4A4 | Howl (Factory New)",
    "M4A4 | Howl (Minimal Wear)",
    "M4A4 | Howl (Field-Tested)",
    "M4A4 | Asiimov (Factory New)",
    "M4A4 | Asiimov (Field-Tested)",
    "M4A4 | Poseidon (Factory New)",
    "M4A4 | Poseidon (Minimal Wear)",
    "M4A4 | The Emperor (Factory New)",
    "M4A4 | The Emperor (Minimal Wear)",
    "M4A4 | Neo-Noir (Factory New)",
    "M4A4 | Neo-Noir (Minimal Wear)",
    "M4A4 | Desolate Space (Factory New)",
    "M4A4 | In Living Color (Factory New)",
    "M4A4 | Temukau (Factory New)",
    "M4A4 | Spider Lily (Factory New)",
    "M4A1-S | Hot Rod (Factory New)",
    "M4A1-S | Hyper Beast (Factory New)",
    "M4A1-S | Hyper Beast (Minimal Wear)",
    "M4A1-S | Chantico's Fire (Factory New)",
    "M4A1-S | Golden Coil (Factory New)",
    "M4A1-S | Decimator (Factory New)",
    "M4A1-S | Printstream (Factory New)",
    "M4A1-S | Printstream (Minimal Wear)",
    "M4A1-S | Welcome to the Jungle (Factory New)",
    "M4A1-S | Blue Phosphor (Factory New)",
    "M4A1-S | Player Two (Factory New)",
    "M4A1-S | Emphorosaur-S (Factory New)",
    "Desert Eagle | Blaze (Factory New)",
    "Desert Eagle | Kumicho Dragon (Factory New)",
    "Desert Eagle | Printstream (Factory New)",
    "Desert Eagle | Code Red (Factory New)",
    "Desert Eagle | Mecha Industries (Factory New)",
    "Desert Eagle | Golden Koi (Factory New)",
    "Desert Eagle | Fennec Fox (Factory New)",
    "Desert Eagle | Ocean Drive (Factory New)",
    "USP-S | Kill Confirmed (Factory New)",
    "USP-S | Kill Confirmed (Minimal Wear)",
    "USP-S | Neo-Noir (Factory New)",
    "USP-S | Printstream (Factory New)",
    "USP-S | The Traitor (Factory New)",
    "USP-S | Cortex (Factory New)",
    "USP-S | Caiman (Factory New)",
    "USP-S | Cyrex (Factory New)",
    "Glock-18 | Fade (Factory New)",
    "Glock-18 | Dragon Tattoo (Factory New)",
    "Glock-18 | Water Elemental (Factory New)",
    "Glock-18 | Bullet Queen (Factory New)",
    "Glock-18 | Gamma Doppler (Factory New)",
    "Glock-18 | Vogue (Factory New)",
    "Glock-18 | Wasteland Rebel (Factory New)",
    "★ Karambit | Doppler (Factory New)",
    "★ Karambit | Fade (Factory New)",
    "★ Karambit | Tiger Tooth (Factory New)",
    "★ Karambit | Marble Fade (Factory New)",
    "★ Karambit | Gamma Doppler (Factory New)",
    "★ Karambit | Crimson Web (Factory New)",
    "★ Karambit | Crimson Web (Minimal Wear)",
    "★ Karambit | Slaughter (Factory New)",
    "★ Karambit | Case Hardened (Factory New)",
    "★ Karambit | Autotronic (Factory New)",
    "★ Karambit | Lore (Factory New)",
    "★ M9 Bayonet | Doppler (Factory New)",
    "★ M9 Bayonet | Fade (Factory New)",
    "★ M9 Bayonet | Tiger Tooth (Factory New)",
    "★ M9 Bayonet | Marble Fade (Factory New)",
    "★ M9 Bayonet | Gamma Doppler (Factory New)",
    "★ M9 Bayonet | Crimson Web (Factory New)",
    "★ M9 Bayonet | Slaughter (Factory New)",
    "★ M9 Bayonet | Lore (Factory New)",
    "★ Butterfly Knife | Doppler (Factory New)",
    "★ Butterfly Knife | Fade (Factory New)",
    "★ Butterfly Knife | Tiger Tooth (Factory New)",
    "★ Butterfly Knife | Marble Fade (Factory New)",
    "★ Butterfly Knife | Gamma Doppler (Factory New)",
    "★ Butterfly Knife | Crimson Web (Factory New)",
    "★ Butterfly Knife | Slaughter (Factory New)",
    "★ Butterfly Knife | Lore (Factory New)",
    "★ Talon Knife | Doppler (Factory New)",
    "★ Talon Knife | Fade (Factory New)",
    "★ Talon Knife | Tiger Tooth (Factory New)",
    "★ Talon Knife | Marble Fade (Factory New)",
    "★ Bayonet | Doppler (Factory New)",
    "★ Bayonet | Fade (Factory New)",
    "★ Bayonet | Tiger Tooth (Factory New)",
    "★ Bayonet | Marble Fade (Factory New)",
    "★ Flip Knife | Doppler (Factory New)",
    "★ Flip Knife | Fade (Factory New)",
    "★ Flip Knife | Tiger Tooth (Factory New)",
    "★ Flip Knife | Marble Fade (Factory New)",
    "★ Gut Knife | Doppler (Factory New)",
    "★ Gut Knife | Fade (Factory New)",
    "★ Huntsman Knife | Doppler (Factory New)",
    "★ Huntsman Knife | Fade (Factory New)",
    "★ Falchion Knife | Doppler (Factory New)",
    "★ Falchion Knife | Fade (Factory New)",
    "★ Shadow Daggers | Doppler (Factory New)",
    "★ Shadow Daggers | Fade (Factory New)",
    "★ Bowie Knife | Doppler (Factory New)",
    "★ Bowie Knife | Fade (Factory New)",
    "★ Ursus Knife | Doppler (Factory New)",
    "★ Ursus Knife | Fade (Factory New)",
    "★ Navaja Knife | Doppler (Factory New)",
    "★ Stiletto Knife | Doppler (Factory New)",
    "★ Paracord Knife | Fade (Factory New)",
    "★ Survival Knife | Fade (Factory New)",
    "★ Nomad Knife | Fade (Factory New)",
    "★ Skeleton Knife | Fade (Factory New)",
    "★ Classic Knife | Fade (Factory New)",
    "★ Kukri Knife | Doppler (Factory New)",
    "★ Kukri Knife | Fade (Factory New)",
    "★ Sport Gloves | Pandora's Box (Factory New)",
    "★ Sport Gloves | Pandora's Box (Minimal Wear)",
    "★ Sport Gloves | Pandora's Box (Field-Tested)",
    "★ Sport Gloves | Superconductor (Factory New)",
    "★ Sport Gloves | Superconductor (Minimal Wear)",
    "★ Sport Gloves | Vice (Factory New)",
    "★ Sport Gloves | Vice (Minimal Wear)",
    "★ Sport Gloves | Slingshot (Factory New)",
    "★ Sport Gloves | Slingshot (Minimal Wear)",
    "★ Specialist Gloves | Crimson Kimono (Factory New)",
    "★ Specialist Gloves | Crimson Kimono (Minimal Wear)",
    "★ Specialist Gloves | Fade (Factory New)",
    "★ Specialist Gloves | Fade (Minimal Wear)",
    "★ Specialist Gloves | Marble Fade (Factory New)",
    "★ Driver Gloves | King Snake (Factory New)",
    "★ Driver Gloves | King Snake (Minimal Wear)",
    "★ Moto Gloves | Spearmint (Factory New)",
    "★ Moto Gloves | Spearmint (Minimal Wear)",
    "★ Hand Wraps | Cobalt Skulls (Factory New)",
    "★ Hand Wraps | Cobalt Skulls (Minimal Wear)",
    "★ Hydra Gloves | Case Hardened (Factory New)",
    "★ Hydra Gloves | Emerald (Factory New)",
    "Copenhagen 2024 Challengers Sticker Capsule",
    "Copenhagen 2024 Contenders Sticker Capsule",
    "Copenhagen 2024 Legends Sticker Capsule",
    "Copenhagen 2024 Champions Autograph Capsule",
    "Paris 2023 Challengers Sticker Capsule",
    "Paris 2023 Contenders Sticker Capsule",
    "Paris 2023 Legends Sticker Capsule",
    "Paris 2023 Champions Autograph Capsule",
    "Rio 2022 Challengers Sticker Capsule",
    "Rio 2022 Contenders Sticker Capsule",
    "Rio 2022 Legends Sticker Capsule",
    "Rio 2022 Champions Autograph Capsule",
    "Antwerp 2022 Challengers Sticker Capsule",
    "Antwerp 2022 Contenders Sticker Capsule",
    "Antwerp 2022 Legends Sticker Capsule",
    "Antwerp 2022 Champions Autograph Capsule",
    "Stockholm 2021 Challengers Sticker Capsule",
    "Stockholm 2021 Contenders Sticker Capsule",
    "Stockholm 2021 Legends Sticker Capsule",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

CONCURRENCY = 5  # Parallel downloads — be polite to csgodatabase.com


async def seed(force: bool = False) -> None:
    if not r2_storage.is_configured():
        print("❌  R2 not configured. Check your .env file.")
        sys.exit(1)

    print(f"🌱  Seeding {len(ALL_ITEMS)} items to R2 (force={force})...")
    sem = asyncio.Semaphore(CONCURRENCY)

    ok = skipped = failed = 0

    async def process(name: str, client: httpx.AsyncClient) -> None:
        nonlocal ok, skipped, failed
        key = f"{normalize_name(name)}.webp"

        if not force:
            existing = await asyncio.to_thread(r2_storage.get_image, key)
            if existing:
                skipped += 1
                print(f"  ⏭  {name}")
                return

        url = f"{CSGO_DB_BASE}/{normalize_name(name)}.webp"
        try:
            async with sem:
                resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200:
                await asyncio.to_thread(r2_storage.put_image, key, resp.content, "image/webp")
                ok += 1
                print(f"  ✅  {name}")
            else:
                failed += 1
                print(f"  ❌  {name}  (HTTP {resp.status_code})")
        except Exception as e:
            failed += 1
            print(f"  ❌  {name}  ({e})")

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        tasks = [process(name, client) for name in ALL_ITEMS]
        await asyncio.gather(*tasks)

    print(f"\n✅ {ok} uploaded  ⏭ {skipped} skipped  ❌ {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-upload all images")
    args = parser.parse_args()
    asyncio.run(seed(force=args.force))
