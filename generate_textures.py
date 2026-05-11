#!/usr/bin/env python3
"""
Generate AI exoplanet textures via Replicate's FLUX-schnell model.

Setup:
    pip install replicate pillow
    export REPLICATE_API_TOKEN=r8_xxxxx

Run:
    python3 generate_textures.py            # generate any missing
    python3 generate_textures.py --force    # regenerate everything

Cost estimate: ~$0.003 per image × 40 = ~$0.12
"""

import os, sys, json, io, time
from pathlib import Path

try:
    import replicate
    from PIL import Image
except ImportError:
    print("Install deps:  pip install replicate pillow")
    sys.exit(1)

OUT_DIR = Path('./textures/exo/auto')
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT_DIR / 'manifest.json'

# 4–5 prompts per type. Each generates one image.
# Negative-style language is built into prompts since FLUX-schnell has no separate negative field.
PROMPTS = {
    'sub-earth': [
        "A small heavily cratered rocky exoplanet, full disc viewed from deep space, lit from one side, photorealistic NASA artist concept, dark starfield background, no Earth features, no continents",
        "A barren grey-brown sub-Earth world with chains of craters and ridges, full sphere viewed in deep space, photorealistic, alien terrain unlike Mercury",
        "A small icy-rocky exoplanet with frost patches and dark stone, full disc photorealistic render, deep starfield, alien world",
        "A tiny dusty rust-coloured rocky world with subtle crater shadows, full sphere photorealistic exoplanet, no Earth features",
    ],
    'rocky': [
        "A rocky terrestrial exoplanet with brown alien continents and ancient dry seabeds, no oceans, full disc in deep space, photorealistic, lit from one side, not Earth",
        "A red-orange rocky planet with deep canyons and volcanic plains, full sphere viewed from space, photorealistic exoplanet, no recognizable Earth features",
        "A barren rocky world with mottled grey-blue surface, alien continents, no oceans, photorealistic NASA-style artist impression",
        "A dim rocky world around a red dwarf, dark crimson surface with bright crater highlights, full disc photorealistic",
        "A muted brown-grey rocky exoplanet with vast lava plains and ancient impact basins, photorealistic, deep space",
    ],
    'super-earth': [
        "A massive rocky super-Earth exoplanet with thick hazy atmosphere and dark continents, full disc in deep space, photorealistic, alien hydrosphere",
        "A volcanic super-Earth with glowing magma rivers and obsidian-black plains, full sphere photorealistic, no Earth features",
        "A super-Earth covered in deep teal water oceans and small rocky continents, thin clouds, alien world, photorealistic",
        "A purple-tinted super-Earth with exotic sulfur atmosphere and metallic surface highlights, photorealistic exoplanet portrait",
        "A heavy rocky super-Earth with rust-red dunes and dark basalt highlands, hazy atmosphere, photorealistic, deep space",
    ],
    'mini-neptune': [
        "A mini-Neptune exoplanet with thick teal hazy atmosphere and soft horizontal cloud bands, photorealistic, full disc viewed from deep space",
        "A Hycean world: mini-Neptune wrapped in deep blue ocean clouds, hydrogen atmosphere, faint streaks, photorealistic exoplanet",
        "A pale lavender steamy mini-Neptune with horizontal cloud striations and bright polar cap, photorealistic",
        "A mini-Neptune with greenish methane atmosphere and faint cyclonic storm patterns, deep space, photorealistic",
    ],
    'neptune': [
        "A deep blue Neptune-class ice giant exoplanet with horizontal cloud bands and a dark equatorial storm, full sphere, photorealistic, deep space",
        "An aqua-blue ice giant with subtle bands and a dark polar vortex, photorealistic exoplanet, NASA artist concept",
        "A pale cyan Neptune-like planet with bright white wispy cloud streaks across its disc, photorealistic, alien ice giant",
        "A dark teal ice giant with prominent dark spot storms and bright cirrus clouds, photorealistic, full disc",
    ],
    'saturn': [
        "A pale gold Saturn-class gas giant exoplanet with thin cream cloud bands, NO RINGS, photorealistic, full sphere, deep space",
        "A cream and butter-coloured gas giant with delicate horizontal bands and a single dark oval storm, NO RINGS, photorealistic",
        "A peach-toned gas giant with elaborate swirling cloud patterns, NO RINGS, photorealistic exoplanet portrait",
        "A pale yellow-tan gas giant with crisp horizontal bands and small white storms, NO RINGS, photorealistic, full disc",
    ],
    'hot-jupiter': [
        "A glowing hot Jupiter exoplanet with bright orange-gold cloud bands and intense storms, NO RINGS, photorealistic, full disc, deep space",
        "A hot Jupiter with deep red-orange atmosphere showing molten dayside glow, NO RINGS, photorealistic exoplanet",
        "A hot Jupiter with metallic silver-grey clouds, dark equatorial belt, NO RINGS, photorealistic, alien world",
        "A hot Jupiter with violent golden-pink atmospheric vortices, NO RINGS, NASA artist impression, photorealistic",
        "A bright amber hot Jupiter with prominent horizontal cloud streaks, NO RINGS, photorealistic, full sphere",
    ],
    'ultra-hot': [
        "An ultra-hot Jupiter exoplanet with magma-glowing dayside and dark nightside, NO RINGS, photorealistic, deep space",
        "A puffy red-orange ultra-hot Jupiter with stellar radiation stripping its atmosphere into a glowing tail, NO RINGS, photorealistic",
        "An ultra-hot Jupiter with white-hot dayside blending into deep crimson terminator, NO RINGS, photorealistic exoplanet",
        "An ultra-hot Jupiter stretched into an egg shape by tidal forces, glowing molten surface, NO RINGS, photorealistic",
    ],
    'cold-gas': [
        "A cold distant gas giant exoplanet with deep navy and steel-blue stormy atmosphere, NO RINGS, photorealistic, far from its star, deep space",
        "A cold gas giant with rich brown cloud bands and white ammonia storms, Jupiter-like but more muted, NO RINGS, photorealistic",
        "A cold gas giant with purple-blue methane tints and bright haze, NO RINGS, photorealistic exoplanet portrait",
        "A dark indigo cold gas giant with subtle cloud structure and dim illumination, NO RINGS, photorealistic, full disc",
    ],
}

def generate(prompt, out_path):
    """Generate one image via FLUX-schnell, resize to 512x512, save as JPG."""
    print(f"  → {out_path.name}", flush=True)
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input={
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "output_format": "jpg",
            "output_quality": 85,
            "num_outputs": 1,
            "go_fast": True,
            "megapixels": "1",
        },
    )
    # output is a list of file-like objects
    img_bytes = output[0].read() if hasattr(output[0], 'read') else output[0]
    if isinstance(img_bytes, str):  # if it's a URL
        import urllib.request
        with urllib.request.urlopen(img_bytes) as r:
            img_bytes = r.read()
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    img = img.resize((512, 512), Image.LANCZOS)
    img.save(out_path, 'JPEG', quality=82, optimize=True)

def main():
    force = '--force' in sys.argv
    if not os.environ.get('REPLICATE_API_TOKEN'):
        print("Set REPLICATE_API_TOKEN env var first.")
        sys.exit(1)

    total = sum(len(v) for v in PROMPTS.values())
    print(f"Plan: {total} images, ~${total * 0.003:.2f} on FLUX-schnell")
    print(f"Output: {OUT_DIR}/")
    input("Press Enter to continue, Ctrl-C to cancel… ")

    manifest = {}
    for type_name, prompts in PROMPTS.items():
        print(f"\n[{type_name}]  {len(prompts)} variants")
        files = []
        for i, prompt in enumerate(prompts, 1):
            fname = f"{type_name}-{i}.jpg"
            out_path = OUT_DIR / fname
            files.append(fname)
            if out_path.exists() and not force:
                print(f"  ✓ {fname} (exists, skipping)")
                continue
            try:
                generate(prompt, out_path)
            except Exception as e:
                print(f"  ✗ {fname} failed: {e}")
                time.sleep(2)
        manifest[type_name] = files

    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nDone. Manifest written to {MANIFEST}")
    print(f"Total files: {len(list(OUT_DIR.glob('*.jpg')))}")

if __name__ == '__main__':
    main()
