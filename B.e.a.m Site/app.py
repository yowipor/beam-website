from flask import Flask, render_template_string, request
import json
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


class CraftParser:
    def __init__(self, base_dir: Path, mappings_file: str = "mappings.json", recipes_file: str = "recipes.json"):
        mappings_data = load_json(base_dir / mappings_file)
        self.recipes = load_json(base_dir / recipes_file)

        craft_aliases = mappings_data.get("craft_aliases", {})
        if not craft_aliases:
            raise ValueError("mappings.json is missing 'craft_aliases'.")

        self.alias_to_craft = {}
        self.sorted_aliases = []

        for craft_name, aliases in craft_aliases.items():
            self.alias_to_craft[craft_name.lower()] = craft_name.lower()
            for alias in aliases:
                self.alias_to_craft[alias.lower()] = craft_name.lower()

        self.sorted_aliases = sorted(self.alias_to_craft.keys(), key=len, reverse=True)

    def split_entries(self, text: str):
        raw = re.split(r"[,;\n]+", text)
        return [entry.strip() for entry in raw if entry.strip()]

    def extract_label(self, entry: str) -> str:
        if " - " in entry:
            return normalize_text(entry.split(" - ", 1)[0])
        if ":" in entry:
            return normalize_text(entry.split(":", 1)[0])
        return normalize_text(entry)

    def clean_item_display(self, entry: str) -> str:
        return re.sub(r"\s+", " ", entry.strip())

    def map_label(self, label: str):
        if label in self.alias_to_craft:
            return self.alias_to_craft[label]

        if label.endswith("s") and label[:-1] in self.alias_to_craft:
            return self.alias_to_craft[label[:-1]]
        if (label + "s") in self.alias_to_craft:
            return self.alias_to_craft[label + "s"]

        for alias in self.sorted_aliases:
            if label == alias or alias in label or label in alias:
                return self.alias_to_craft[alias]

        return None

    def parse(self, text: str):
        counts = defaultdict(int)
        unmapped = []
        itemized = []

        for entry in self.split_entries(text):
            itemized.append(self.clean_item_display(entry))
            label = self.extract_label(entry)
            craft = self.map_label(label)
            if craft:
                counts[craft] += 1
            else:
                unmapped.append(label.title())

        return dict(sorted(counts.items())), sorted(set(unmapped)), itemized

    def build_summaries(self, counts):
        total_cost = 0
        material_totals = defaultdict(int)

        for craft, qty in counts.items():
            recipe = self.recipes.get(craft)
            if not recipe:
                continue

            total_cost += int(recipe.get("value", 0)) * qty

            for material, amount in recipe.get("materials", {}).items():
                material_totals[material] += int(amount) * qty

        return total_cost, dict(sorted(material_totals.items()))


parser = CraftParser(BASE_DIR, "mappings.json", "recipes.json")
app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>B.E.A.M</title>
  <style>
    :root{
      --bg:#07090d;
      --panel:rgba(12,16,24,.78);
      --panel-2:rgba(20,25,35,.86);
      --line:rgba(255,255,255,.12);
      --text:#f5f7fb;
      --muted:#c6cfdb;
      --accent:#ff4f87;
      --accent-2:#7c5cff;
      --good:#4ade80;
      --bad:#f87171;
      --shadow:0 18px 50px rgba(0,0,0,.35);
      --radius:22px;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      min-height:100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      color:var(--text);
      background:
        linear-gradient(rgba(4,7,12,.55), rgba(4,7,12,.75)),
        url('/static/bg.jpg') center center / cover fixed no-repeat,
        var(--bg);
    }
    .page{
      max-width:1200px;
      margin:0 auto;
      padding:28px 18px 36px;
    }
    .hero{
      border:1px solid var(--line);
      background:linear-gradient(180deg, rgba(18,23,34,.74), rgba(10,14,21,.84));
      backdrop-filter: blur(12px);
      border-radius:28px;
      box-shadow:var(--shadow);
      padding:26px;
      margin-bottom:18px;
    }
    .brand{
      display:flex;
      align-items:end;
      gap:14px;
      flex-wrap:wrap;
      margin-bottom:10px;
    }
    .brand h1{
      margin:0;
      font-size: clamp(2rem, 4vw, 3.6rem);
      letter-spacing:.08em;
      line-height:1;
      text-transform:uppercase;
      text-shadow:0 4px 18px rgba(0,0,0,.3);
    }
    .tag{
      display:inline-flex;
      align-items:center;
      padding:7px 12px;
      border-radius:999px;
      font-size:.85rem;
      color:#fff;
      background:linear-gradient(135deg, var(--accent), var(--accent-2));
      box-shadow:0 8px 20px rgba(124,92,255,.28);
    }
    .sub{
      color:var(--muted);
      margin:0 0 18px;
      max-width:760px;
      font-size:1rem;
      line-height:1.5;
    }
    .input-wrap{
      display:flex;
      flex-direction:column;
      gap:12px;
    }
    textarea{
      width:100%;
      min-height:190px;
      resize:vertical;
      border-radius:20px;
      border:1px solid rgba(255,255,255,.14);
      background:rgba(6,10,16,.72);
      color:var(--text);
      padding:18px 18px;
      font:inherit;
      line-height:1.5;
      outline:none;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.03);
    }
    textarea:focus{
      border-color:rgba(255,79,135,.65);
      box-shadow:0 0 0 4px rgba(255,79,135,.14);
    }
    .actions{
      display:flex;
      gap:12px;
      flex-wrap:wrap;
      align-items:center;
    }
    button{
      appearance:none;
      border:none;
      border-radius:16px;
      padding:14px 18px;
      font:inherit;
      font-weight:700;
      color:white;
      cursor:pointer;
      background:linear-gradient(135deg, var(--accent), var(--accent-2));
      box-shadow:0 14px 30px rgba(124,92,255,.28);
    }
    .hint{
      color:var(--muted);
      font-size:.95rem;
    }
    .grid{
      display:grid;
      grid-template-columns:repeat(12,1fr);
      gap:16px;
    }
    .card{
      grid-column:span 6;
      border:1px solid var(--line);
      background:linear-gradient(180deg, rgba(17,21,31,.84), rgba(11,14,21,.9));
      backdrop-filter: blur(10px);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      overflow:hidden;
    }
    .card.full{grid-column:1/-1}
    .card-header{
      padding:16px 18px 12px;
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      border-bottom:1px solid rgba(255,255,255,.06);
    }
    .card-title{
      margin:0;
      font-size:1.02rem;
      letter-spacing:.01em;
    }
    .count-badge{
      min-width:34px;
      padding:6px 10px;
      border-radius:999px;
      text-align:center;
      color:#fff;
      font-size:.84rem;
      background:rgba(255,255,255,.08);
      border:1px solid rgba(255,255,255,.08);
    }
    .card-body{
      padding:16px 18px 18px;
    }
    ul.clean{
      list-style:none;
      margin:0;
      padding:0;
      display:grid;
      gap:10px;
    }
    ul.clean li{
      display:flex;
      justify-content:space-between;
      gap:14px;
      padding:11px 12px;
      border-radius:14px;
      background:rgba(255,255,255,.04);
      border:1px solid rgba(255,255,255,.05);
      align-items:flex-start;
    }
    ul.clean li .label{
      color:var(--text);
      font-weight:600;
    }
    ul.clean li .value{
      color:#fff;
      font-weight:800;
      white-space:nowrap;
    }
    .item-list li{
      justify-content:flex-start;
      color:#eef2f8;
      font-weight:500;
    }
    .pill{
      display:inline-flex;
      align-items:center;
      justify-content:center;
      gap:8px;
      min-height:42px;
      padding:10px 14px;
      border-radius:14px;
      background:rgba(255,255,255,.05);
      border:1px solid rgba(255,255,255,.08);
      font-weight:800;
    }
    .cost{
      font-size:2rem;
      font-weight:900;
      letter-spacing:.02em;
    }
    .empty{
      color:var(--muted);
      margin:0;
    }
    .footer{
      margin-top:18px;
      color:rgba(255,255,255,.72);
      font-size:.92rem;
      text-align:center;
    }
    @media (max-width: 900px){
      .card{grid-column:1/-1}
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="brand">
        <h1>B.E.A.M</h1>
        <span class="tag">Benny's Ergonomic Assist Module</span>
      </div>
      <p class="sub">Paste a cosmetic list from your sheet and get the exact item list, craft counts, materials needed, and total value in one clean view.</p>

      <form method="post" class="input-wrap">
        <textarea name="build_text" placeholder="Paste the vehicle sheet here...">{{ build_text }}</textarea>
        <div class="actions">
          <button type="submit">Calculate Build</button>
          <span class="hint">Works with comma-separated or line-by-line sheet text.</span>
        </div>
      </form>
    </section>

    {% if result %}
    <section class="grid">
      <article class="card full">
        <div class="card-header">
          <h2 class="card-title">Items From Sheet</h2>
          <span class="count-badge">{{ result.itemized|length }}</span>
        </div>
        <div class="card-body">
          {% if result.itemized %}
          <ul class="clean item-list">
            {% for item in result.itemized %}
            <li>{{ item }}</li>
            {% endfor %}
          </ul>
          {% else %}
          <p class="empty">No items found.</p>
          {% endif %}
        </div>
      </article>

      <article class="card">
        <div class="card-header">
          <h2 class="card-title">Craft Requirements</h2>
          <span class="count-badge">{{ result.total_crafts }}</span>
        </div>
        <div class="card-body">
          {% if result.counts %}
          <ul class="clean">
            {% for craft, qty in result.counts.items() %}
            <li><span class="label">{{ craft }}</span><span class="value">{{ qty }}</span></li>
            {% endfor %}
          </ul>
          {% else %}
          <p class="empty">No mapped crafts found.</p>
          {% endif %}
        </div>
      </article>

      <article class="card">
        <div class="card-header">
          <h2 class="card-title">Materials Summary</h2>
          <span class="count-badge">{{ result.material_totals|length }}</span>
        </div>
        <div class="card-body">
          {% if result.material_totals %}
          <ul class="clean">
            {% for material, qty in result.material_totals.items() %}
            <li><span class="label">{{ material.replace('_', ' ').title() }}</span><span class="value">{{ qty }}</span></li>
            {% endfor %}
          </ul>
          {% else %}
          <p class="empty">No materials calculated.</p>
          {% endif %}
        </div>
      </article>

      <article class="card {% if result.unmapped %} {% else %}full{% endif %}">
        <div class="card-header">
          <h2 class="card-title">Total Value</h2>
          <span class="count-badge">$</span>
        </div>
        <div class="card-body">
          <div class="pill cost">${{ "{:,}".format(result.total_cost) }}</div>
        </div>
      </article>

      {% if result.unmapped %}
      <article class="card">
        <div class="card-header">
          <h2 class="card-title">Unmapped Labels</h2>
          <span class="count-badge">{{ result.unmapped|length }}</span>
        </div>
        <div class="card-body">
          <ul class="clean item-list">
            {% for label in result.unmapped %}
            <li>{{ label }}</li>
            {% endfor %}
          </ul>
        </div>
      </article>
      {% endif %}
    </section>
    {% endif %}

    <div class="footer">Built for fast sheet checking and craft planning.</div>
  </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    build_text = ""
    result = None

    if request.method == "POST":
        build_text = request.form.get("build_text", "")
        counts, unmapped, itemized = parser.parse(build_text)
        total_cost, material_totals = parser.build_summaries(counts)

        result = {
            "itemized": itemized,
            "counts": counts,
            "total_crafts": sum(counts.values()),
            "material_totals": material_totals,
            "total_cost": total_cost,
            "unmapped": unmapped
        }

    return render_template_string(TEMPLATE, build_text=build_text, result=result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
