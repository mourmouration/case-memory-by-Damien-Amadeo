#!/usr/bin/env python3
"""Чтение и проверка памяти по делам в папке «0.3. Memory/».

Только stdlib, без сети. Ничего не записывает и не изменяет.

Команды:
  status DIR [--today ГГГГ-ММ-ДД]
      Состояние памяти: число карточек, сессий и уроков; сессии новее карточки
      дела; расхождения index.md с projects/; карточки «в работе» без обновления
      60+ дней; дела с 8+ файлами сессий; строки lessons.md без причины или тегов,
      похожие теги. В конце – нужен ли режим CONSOLIDATE и почему.

  recall DIR КЛЮЧ [КЛЮЧ ...] [--sessions] [--all-sections]
      Поиск по опыту всех дел. Ключи – слова или регулярные выражения; регистр
      и «ё/е» не различаются при любой локали. Слои: lessons.md → карточки
      projects/ (только разделы «Актуальные правовые позиции» и «Что не работало»,
      с --all-sections – все) → sessions/ (если первые два слоя пусты или задан
      --sessions). Находки упорядочены по числу совпавших ключей.

  lessons DIR [--tags #тег ...] [--exclude-case ДЕЛО]
      Число уроков по тегам, без уроков самого дела. Сами уроки не выводятся.

  nextname DIR ДЕЛО [--date ГГГГ-ММ-ДД] [--summary]
      Свободное имя файла сессии: sessions/ГГГГ-ММ-ДД_дело.md, при совпадении –
      с номером; --summary – для промежуточной сводки режима COMPRESS.

DIR – путь к «0.3. Memory/» либо к ее копии (файлы, полученные через
device_stage_files). Даты берутся из имен файлов и поля «Обновлено», а не из
времени изменения файла, поэтому копия дает тот же результат. Файлы из раздела
«Архив» index.md и из подпапок archive/ в расчет не идут.

Все команды принимают --json.
"""
import argparse
import datetime
import json
import os
import re
import sys

RECALL_SECTIONS = ("актуальные правовые позиции", "что не работало")
STALE_DAYS = 60
MANY_SESSIONS_TOTAL = 15
MANY_SESSIONS_CASE = 8


def norm(s):
    return s.lower().replace("ё", "е")


def slug(s):
    return re.sub(r"[^0-9a-zа-я]+", "", norm(s))


def parse_date(s):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s or "")
        if not m:
            return None
        d, mo, y = map(int, m.groups())
    try:
        return datetime.date(y, mo, d)
    except ValueError:
        return None


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def md_files(folder):
    out = []
    if os.path.isdir(folder):
        for root, dirs, names in os.walk(folder):
            dirs[:] = [d for d in dirs if d.lower() not in ("archive", "архив")]
            out += [os.path.join(root, n) for n in sorted(names) if n.lower().endswith(".md")]
    return sorted(out)


class Memory:
    def __init__(self, root):
        if not os.path.isdir(root):
            sys.exit(f"Папка не найдена: {root}")
        self.root = root
        self.index_text = read(os.path.join(root, "index.md")) if os.path.isfile(os.path.join(root, "index.md")) else ""
        self.archived = self._archived()
        self.cards = [c for c in (self._card(p) for p in md_files(os.path.join(root, "projects"))) if c]
        self.sessions = [s for s in (self._session(p) for p in md_files(os.path.join(root, "sessions"))) if s]
        self.lessons = self._lessons()
        self.index_rows = self._index_rows()

    def rel(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def _archived(self):
        out = set()
        m = re.search(r"(?mi)^##\s*архив\b.*$", self.index_text)
        if m:
            for ln in self.index_text[m.end():].split("\n"):
                if ln.startswith("## "):
                    break
                f = re.match(r"\s*[-*]\s*`?([^`—–|]+?\.md)`?", ln)
                if f:
                    out.add(f.group(1).strip().replace("\\", "/"))
        return out

    def _card(self, path):
        rel = self.rel(path)
        text = read(path)
        if rel in self.archived or re.search(r"(?mi)^>?\s*архив\b", "\n".join(text.split("\n")[:5])):
            return None

        def field(name):
            m = re.search(rf"(?mi)^\*\*{name}:?\*\*:?\s*(.+)$", text)
            return m.group(1).strip() if m else ""

        title = re.search(r"(?m)^#\s+(?:Дело:\s*)?(.+)$", text)
        return {"файл": rel, "дело": os.path.splitext(os.path.basename(path))[0],
                "название": title.group(1).strip() if title else "", "статус": field("Статус"),
                "обновлено": parse_date(field("Обновлено")), "теги": re.findall(r"#[\w.\-]+", field("Теги")),
                "текст": text}

    def _session(self, path):
        rel = self.rel(path)
        if rel in self.archived:
            return None
        name = os.path.splitext(os.path.basename(path))[0]
        m = re.match(r"(\d{4}-\d{2}-\d{2})[_ ](.+)$", name)
        if not m:
            return {"файл": rel, "дата": None, "дело": name, "сводка": False, "путь": path}
        case = re.sub(r"([_-](v\d+|\d{1,2}|сводка|summary))+$", "", m.group(2), flags=re.I)
        return {"файл": rel, "дата": parse_date(m.group(1)), "дело": case,
                "сводка": bool(re.search(r"сводка|summary", m.group(2), re.I)), "путь": path}

    def _lessons(self):
        path = os.path.join(self.root, "lessons.md")
        out = []
        if not os.path.isfile(path):
            return out
        for i, ln in enumerate(read(path).split("\n"), 1):
            if not ln.lstrip().startswith("- ") or "|" not in ln:
                continue
            parts = [p.strip() for p in ln.lstrip()[2:].split("|", 3)]
            parts += [""] * (4 - len(parts))
            body = re.split(r"\s·\s", parts[3])[0]
            chain = [x.strip() for x in body.split("→")]
            out.append({"строка": i, "текст": ln.strip(), "дата": parse_date(parts[0]), "дело": parts[1],
                        "теги": re.findall(r"#[\w.\-]+", parts[2]),
                        "есть_причина": len(chain) >= 3 and bool(chain[2]),
                        "устарел": "УСТАРЕЛ" in ln})
        return out

    def _index_rows(self):
        rows = []
        for ln in self.index_text.split("\n"):
            if ln.startswith("## "):
                break
            if not ln.strip().startswith("|"):
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 2 and not set(cells[0]) <= set("-: ") and norm(cells[0]) != "дело":
                rows.append({"дело": cells[0], "статус": cells[1] if len(cells) > 1 else "",
                             "последняя_сессия": cells[2] if len(cells) > 2 else ""})
        return rows

    def card_for(self, name):
        key = slug(name)
        if not key:
            return None
        for c in self.cards:
            if key in (slug(c["дело"]), slug(c["название"])):
                return c
        for c in self.cards:
            for other in (slug(c["дело"]), slug(c["название"])):
                if len(other) >= 5 and len(key) >= 5 and (key in other or other in key):
                    return c
        return None


# ------------------------------------------------------------------ status

def cmd_status(mem, a):
    today = parse_date(a.today) if a.today else datetime.date.today()
    per_case = {}
    for s in mem.sessions:
        card = mem.card_for(s["дело"])
        per_case.setdefault(card["дело"] if card else s["дело"], []).append(s)

    newer, closed_growing = {}, []
    for case, ss in per_case.items():
        card = mem.card_for(case)
        if not card:
            continue
        fresh = [s["файл"] for s in ss if s["дата"] and (not card["обновлено"] or s["дата"] > card["обновлено"])]
        if fresh:
            newer[case] = sorted(fresh)
            if "заверш" in norm(card["статус"]):
                closed_growing.append(case)

    no_row = [c["дело"] for c in mem.cards
              if not any(mem.card_for(r["дело"]) is c for r in mem.index_rows)]
    no_card = [r["дело"] for r in mem.index_rows if not mem.card_for(r["дело"])]
    orphan_sessions = sorted({s["дело"] for s in mem.sessions if not mem.card_for(s["дело"])})
    stale = [f"{c['дело']} (обновлено {c['обновлено']})" for c in mem.cards
             if "работ" in norm(c["статус"]) and c["обновлено"] and (today - c["обновлено"]).days >= STALE_DAYS]
    no_date = [c["дело"] for c in mem.cards if not c["обновлено"]]
    many = {k: len(v) for k, v in per_case.items() if len(v) >= MANY_SESSIONS_CASE}

    tags = sorted({t for l in mem.lessons for t in l["теги"]})
    similar = [f"{x} / {y}" for i, x in enumerate(tags) for y in tags[i + 1:]
               if len(os.path.commonprefix([slug(x), slug(y)])) >= 6]
    les = {"всего": len(mem.lessons), "без_причины": [l["строка"] for l in mem.lessons if not l["есть_причина"]],
           "без_тегов": [l["строка"] for l in mem.lessons if not l["теги"]],
           "без_даты": [l["строка"] for l in mem.lessons if not l["дата"]],
           "устаревших": sum(l["устарел"] for l in mem.lessons), "похожие_теги": similar}

    reasons = []
    if len(mem.sessions) >= MANY_SESSIONS_TOTAL:
        reasons.append(f"в sessions/ {len(mem.sessions)} файлов вне архива")
    if many:
        reasons.append("8+ сессий по делу: " + ", ".join(f"{k} ({v})" for k, v in many.items()))
    if no_row or no_card:
        reasons.append("index.md расходится с projects/")
    if closed_growing:
        reasons.append("по завершенным делам копятся сессии: " + ", ".join(closed_growing))
    if stale:
        reasons.append("карточки «в работе» без обновления 60+ дней: " + ", ".join(stale))
    if les["без_причины"] or les["похожие_теги"]:
        reasons.append("lessons.md: строки без причины или похожие теги")

    res = {"карточек": len(mem.cards), "сессий_вне_архива": len(mem.sessions), "в_архиве_по_индексу": len(mem.archived),
           "уроков": les, "сессии_новее_карточки": newer, "карточки_без_строки_в_индексе": no_row,
           "строки_индекса_без_карточки": no_card, "сессии_без_карточки": orphan_sessions,
           "карточки_без_даты_обновления": no_date, "в_работе_без_обновления_60_дней": stale,
           "много_сессий_по_делу": many, "consolidate": {"нужен": bool(reasons), "причины": reasons}}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return
    print(f"Память: карточек {len(mem.cards)}, сессий вне архива {len(mem.sessions)}, "
          f"в архиве по индексу {len(mem.archived)}, уроков {les['всего']} (устаревших {les['устаревших']})")

    def show(title, items):
        if items:
            print(f"{title}: " + (", ".join(map(str, items)) if isinstance(items, list)
                                   else "; ".join(f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in items.items())))
    show("Сессии новее карточки (не вобраны в карточку)", newer)
    show("Карточки без строки в index.md", no_row)
    show("Строки index.md без карточки", no_card)
    show("Сессии по делам без карточки", orphan_sessions)
    show("Карточки без даты «Обновлено»", no_date)
    show("lessons.md – строки без причины", les["без_причины"])
    show("lessons.md – строки без тегов", les["без_тегов"])
    show("lessons.md – похожие теги", similar)
    print("CONSOLIDATE: " + ("рекомендуется – " + "; ".join(reasons) if reasons else "не требуется"))


# ------------------------------------------------------------------ recall

def compile_keys(keys):
    out = []
    for k in keys:
        try:
            out.append((k, re.compile(norm(k))))
        except re.error:
            out.append((k, re.compile(re.escape(norm(k)))))
    return out


def hits(text, keys):
    t = norm(text)
    return [k for k, rx in keys if rx.search(t)]


def card_blocks(card, all_sections):
    """Пункты карточки (строка списка с продолжениями) вместе с названием раздела."""
    section, block = "", []
    for ln in card["текст"].split("\n") + ["## "]:
        if ln.startswith("#"):
            if block:
                yield section, " ".join(block)
                block = []
            section = ln.lstrip("# ").strip()
            continue
        if not all_sections and not norm(section).startswith(RECALL_SECTIONS):
            continue
        if re.match(r"\s*([-*]|\d+[.)])\s", ln) or not ln.strip():
            if block:
                yield section, " ".join(block)
            block = [ln.strip()] if ln.strip() else []
        else:
            block.append(ln.strip())


def cmd_recall(mem, a):
    keys = compile_keys(a.keys)
    today = datetime.date.today()
    lessons = []
    for l in mem.lessons:
        h = hits(l["текст"], keys)
        if h:
            flags = (["УСТАРЕЛ"] if l["устарел"] else []) + (
                ["старше года – проверить актуальность"] if l["дата"] and (today - l["дата"]).days > 365 else [])
            lessons.append({"ключи": h, "дата": str(l["дата"] or ""), "текст": l["текст"], "пометки": flags,
                            "источник": f"lessons.md:{l['строка']}"})
    positions = []
    for c in mem.cards:
        for section, block in card_blocks(c, a.all_sections):
            h = hits(block, keys)
            if h:
                old = c["обновлено"] and (today - c["обновлено"]).days > 365
                positions.append({"ключи": h, "дело": c["дело"], "статус_дела": c["статус"], "раздел": section,
                                  "текст": block, "обновлено": str(c["обновлено"] or ""),
                                  "пометки": ["карточка старше года – проверить актуальность"] if old else [],
                                  "источник": c["файл"]})
    sessions = []
    if a.sessions or not (lessons or positions):
        for s in mem.sessions:
            for i, ln in enumerate(read(s["путь"]).split("\n"), 1):
                h = hits(ln, keys)
                if h and ln.strip():
                    sessions.append({"ключи": h, "дело": s["дело"], "дата": str(s["дата"] or ""),
                                     "текст": ln.strip(), "источник": f"{s['файл']}:{i}"})
    for lst in (lessons, positions, sessions):
        lst.sort(key=lambda r: r.get("дата") or r.get("обновлено") or "", reverse=True)   # свежие выше
        lst.sort(key=lambda r: -len(r["ключи"]))                                        # больше ключей – выше
    res = {"ключи": a.keys, "уроки": lessons, "позиции": positions, "сессии": sessions}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return

    def flags(r):
        return (" [" + "; ".join(r["пометки"]) + "]") if r.get("пометки") else ""
    print(f"Ключи: {', '.join(a.keys)}")
    print(f"\nУроки: {len(lessons)}")
    for r in lessons:
        print(f"  ({len(r['ключи'])}) {r['текст']}{flags(r)}  ← {r['источник']}")
    print(f"\nПозиции из карточек: {len(positions)}")
    for r in positions:
        print(f"  ({len(r['ключи'])}) {r['дело']} [{r['статус_дела'] or 'статус не указан'}; обновлено {r['обновлено'] or '?'}] "
              f"«{r['раздел']}»: {r['текст']}{flags(r)}  ← {r['источник']}")
    if a.sessions or not (lessons or positions):
        print(f"\nСессии: {len(sessions)}")
        for r in sessions[:60]:
            print(f"  ({len(r['ключи'])}) {r['дело']} {r['дата']}: {r['текст']}  ← {r['источник']}")
    if not (lessons or positions or sessions):
        print("\nВ памяти по этим ключам ничего нет.")


# ------------------------------------------------------------------ lessons / nextname

def cmd_lessons(mem, a):
    want = {norm(t if t.startswith("#") else "#" + t) for t in a.tags}
    skip = slug(a.exclude_case or "")
    rows = [l for l in mem.lessons if not l["устарел"]
            and (not want or want & {norm(t) for t in l["теги"]})
            and not (skip and (skip in slug(l["дело"]) or slug(l["дело"]) in skip) and slug(l["дело"]))]
    by_tag = {}
    for l in rows:
        for t in l["теги"]:
            if not want or norm(t) in want:
                by_tag[t] = by_tag.get(t, 0) + 1
    res = {"уроков": len(rows), "по_тегам": by_tag, "дел": len({slug(l["дело"]) for l in rows})}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"Уроков из других дел: {len(rows)} (дел: {res['дел']})" +
              ("; " + ", ".join(f"{k} – {v}" for k, v in sorted(by_tag.items())) if by_tag else ""))


def cmd_nextname(mem, a):
    date = a.date or datetime.date.today().isoformat()
    base = f"{date}_{a.case}" + ("_сводка" if a.summary else "")
    taken = {os.path.splitext(os.path.basename(p))[0] for p in md_files(os.path.join(mem.root, "sessions"))}
    name, n = base, 2
    while name in taken:
        name, n = f"{base}-{n}", n + 1
    out = f"sessions/{name}.md"
    print(json.dumps({"файл": out}, ensure_ascii=False) if a.json else out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("dir")
    common.add_argument("--json", action="store_true")
    p = sub.add_parser("status", parents=[common])
    p.add_argument("--today")
    p = sub.add_parser("recall", parents=[common])
    p.add_argument("keys", nargs="+")
    p.add_argument("--sessions", action="store_true")
    p.add_argument("--all-sections", action="store_true")
    p = sub.add_parser("lessons", parents=[common])
    p.add_argument("--tags", nargs="*", default=[])
    p.add_argument("--exclude-case")
    p = sub.add_parser("nextname", parents=[common])
    p.add_argument("case")
    p.add_argument("--date")
    p.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    mem = Memory(a.dir)
    {"status": cmd_status, "recall": cmd_recall, "lessons": cmd_lessons, "nextname": cmd_nextname}[a.cmd](mem, a)


if __name__ == "__main__":
    main()
