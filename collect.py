#!/usr/bin/env python3
"""Collect senior job listings from public sources into candidates.json (no logins, read only).

Usage: python3 collect.py [out.json]
       python3 collect.py --gotfriends-only local/gotfriends.json   (run on your own computer)
Prints one line per source: how many senior listings it found, or why it failed.

GotFriends blocks the cloud (403) but answers from a home computer. A scheduled job on your computer can run --gotfriends-only and push local/gotfriends.json; the cloud run
falls back to that file when its own GotFriends fetch fails and the file is under 36 hours old.
"""
import json, os, re, sys, time, html, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
SENIOR = re.compile(r"\b(CTO|Chief Technology|VP|V\.P\.|Vice President|Head of (R&D|RnD|Engineering|Development|Software)|"
                    r"Founding|Co-?founder|Director of (R&D|Engineering)|R&D Director|Engineering Director)\b|סמנכ\"?ל|מנהל/ת פיתוח|מנהל פיתוח|ראש תחום פיתוח", re.I)
NOT_TECH = re.compile(r"\b(Sales|Marketing|Marketer|Go-To-Market|GTM|Finance|Legal|HR|People|Customer Success|Revenue|Partnerships|Security and IT|Design|"
                      r"Account Executive|Operations|Product Growth|Office of the CTO|CTO Office|Team Member|Staff Engineer|Forward Deployed|Assistant|Analyst)\b", re.I)
GETRO = ["jobs.tlv.partners", "jobs.vertexventures.co.il", "careers.grovevc.com", "careers.viola-group.com",
         "jobs.nfx.com", "jobs.insightpartners.com", "jobs.ibexinvestors.com", "jobs.innovationendeavors.com",
         "careers.hetz.vc", "careers.wing.vc", "jobs.accel.com", "jobs.generalcatalyst.com", "jobs.ggvc.com", "jobs.8vc.com"]
ISRAEL = "eyJzZWFyY2hhYmxlX2xvY2F0aW9ucyI6WyJJc3JhZWwiXX0="
TERMS = ["CTO", "VP", "Head of R&D", "Head of Engineering", "Founding"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "he,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def senior(title):
    return bool(SENIOR.search(title)) and not NOT_TECH.search(title)


def gotfriends():
    out = []
    for sub in ["cto-jobs", "vp-rd", "development-executive", "group-manager"]:
        for page in (1, 2):
            url = f"https://www.gotfriends.co.il/jobslobby/executive-position/{sub}/" + (f"?page={page}" if page > 1 else "")
            h = get(url)
            for m in re.finditer(r'href="(/jobslobby/[^"]+/(\d{5,})/)"[^>]*>\s*<h2[^>]*>(.*?)</h2>', h, re.S):
                t = text(m.group(3))
                if t:
                    out.append({"source": "GotFriends", "id": f"GotFriends {m.group(2)}", "title": t, "company": "(anonymised)",
                                "url": "https://www.gotfriends.co.il" + m.group(1)})
            time.sleep(1)
    return out


MAC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local", "gotfriends.json")


def gotfriends_or_mac():
    try:
        return gotfriends()
    except Exception as e:
        try:
            data = json.load(open(MAC_FILE, encoding="utf-8"))
        except (OSError, ValueError):
            raise e
        age = time.time() - data.get("at", 0)
        if age > 36 * 3600:
            raise RuntimeError(f"blocked here, and the Mac's copy is {age / 3600:.0f}h old") from e
        print(f"  GotFriends: blocked here ({type(e).__name__}); using the Mac's copy from {age / 3600:.1f}h ago")
        return data["items"]


def getro():
    out = []
    for board in GETRO:
        for term in TERMS:
            url = f"https://{board}/jobs?q={urllib.parse.quote(term)}&filter={ISRAEL}"
            try:
                h = get(url)
            except Exception as e:
                print(f"  Getro {board} '{term}': skipped ({type(e).__name__})")
                continue
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
            if not m:
                continue
            found = []

            def walk(x):
                if isinstance(x, dict):
                    if "title" in x and ("organization" in x or "companyName" in x) and isinstance(x.get("title"), str):
                        found.append(x)
                    for v in x.values():
                        walk(v)
                elif isinstance(x, list):
                    for v in x:
                        walk(v)
            walk(json.loads(m.group(1)))
            for j in found:
                org = j.get("organization") or {}
                company = org.get("name") if isinstance(org, dict) else j.get("companyName", "")
                slug = org.get("slug", "") if isinstance(org, dict) else ""
                link = j.get("url") or (f"https://{board}/companies/{slug}/jobs/{j.get('slug', '')}" if slug else f"https://{board}/jobs")
                out.append({"source": f"Getro {board}", "id": f"{company} · {j['title']}", "title": j["title"], "company": company or "",
                            "url": link, "locations": j.get("locations") or j.get("searchableLocations"), "created": j.get("createdAt")})
            time.sleep(0.5)
    return out


def team8():
    h = get("https://team8.vc/careers/")
    out = {}
    for m in re.finditer(r'href="https://team8\.vc/career/([^/"]+)/([^/"]+)/?"', h):
        company, slug = m.group(1), m.group(2)
        out[slug] = {"source": "Team8", "id": f"Team8 {company}/{slug}", "title": slug.replace("-", " ").replace("rd", "R&D"),
                     "company": company, "url": f"https://team8.vc/career/{company}/{slug}/"}
    return list(out.values())


def drushim():
    out = []
    for term in ["CTO", "VP R&D", 'סמנכ"ל פיתוח', "Head of R&D"]:
        h = get("https://www.drushim.co.il/jobs/search/" + urllib.parse.quote(term) + "/")
        d = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S).group(1))
        for q in d["props"]["pageProps"]["dehydratedState"]["queries"]:
            for pg in ((q.get("state") or {}).get("data") or {}).get("pages", []) if isinstance((q.get("state") or {}).get("data"), dict) else []:
                for j in pg.get("jobs", []):
                    url = j.get("jobUrl") or ""
                    out.append({"source": "Drushim", "id": f"Drushim {j.get('id')}", "title": j.get("title", ""), "company": j.get("companyName", ""),
                                "url": url if url.startswith("http") else "https://www.drushim.co.il" + url, "created": j.get("publishedAtIso"),
                                "location": j.get("city")})
        time.sleep(1)
    return out


def startupjobs():
    feed = json.loads(get("https://www.startupjobs.co.il/feed/jobs.json"))
    return [{"source": "startupjobs", "id": i.get("url"), "title": i.get("title", ""), "company": i.get("company", ""),
             "url": i.get("url"), "created": i.get("date_published")} for i in feed.get("items", [])]


def secrettelaviv():
    h = get("https://jobs.secrettelaviv.com/")
    return [{"source": "Secret Tel Aviv", "id": m.group(1), "title": text(m.group(2)), "company": "", "url": m.group(1)}
            for m in re.finditer(r'href="(https://jobs\.secrettelaviv\.com/job/[^"]+)"[^>]*>(.*?)</a>', h, re.S) if text(m.group(2))]


def alljobs():
    out = []
    for term in ["CTO", "VP R&D", 'סמנכ"ל פיתוח', "Head of R&D"]:
        h = get("https://www.alljobs.co.il/SearchResultsGuest.aspx?freetxt=" + urllib.parse.quote(term))
        for m in re.finditer(r'href="/Search/UploadSingle\.aspx\?JobID=(\d+)"[^>]*>\s*<h2[^>]*>(.*?)</h2>', h, re.S):
            c = re.search(r'<a href="/Employer/[^"]*">(.*?)</a>', h[m.end():m.end() + 600], re.S)
            out.append({"source": "AllJobs", "id": f"AllJobs {m.group(1)}", "title": text(m.group(2)), "company": text(c.group(1)) if c else "",
                        "url": f"https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID={m.group(1)}"})
        time.sleep(1)
    return out


def hn():
    api = "https://hn.algolia.com/api/v1/"
    hits = json.loads(get(api + "search_by_date?tags=story,author_whoishiring&hitsPerPage=10"))["hits"]
    story = next(h for h in hits if h.get("title", "").startswith("Ask HN: Who is hiring?"))
    out = []
    for c in json.loads(get(api + "items/" + story["objectID"])).get("children", []):
        body = c.get("text") or ""
        if not re.search(r"Israel|Tel[ -]?Aviv", body, re.I):
            continue
        first = text(re.split(r"<p>", body, maxsplit=1)[0])
        out.append({"source": "HN Who is hiring", "id": f"HN {c['id']}", "title": first[:200], "company": first.split("|")[0].strip()[:80],
                    "url": f"https://news.ycombinator.com/item?id={c['id']}", "created": c.get("created_at")})
    return out


def main(out_path):
    seen, results = set(), []
    for name, fn in [("GotFriends", gotfriends_or_mac), ("Getro VC boards", getro), ("Team8", team8), ("Drushim", drushim),
                     ("startupjobs", startupjobs), ("Secret Tel Aviv", secrettelaviv),
                     ("AllJobs", alljobs), ("HN Who is hiring", hn)]:
        try:
            items = [i for i in fn() if senior(i["title"])]
            new = [i for i in items if i["id"] not in seen and not seen.add(i["id"])]
            results += new
            print(f"{name}: {len(new)} senior listings")
        except Exception as e:
            print(f"{name}: FAILED ({type(e).__name__}: {str(e)[:120]})")
    json.dump(results, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"total: {len(results)} -> {out_path}")


def gotfriends_only(out_path):
    items = [i for i in gotfriends() if senior(i["title"])]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    json.dump({"at": time.time(), "items": items}, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"GotFriends: {len(items)} senior listings -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gotfriends-only":
        gotfriends_only(sys.argv[2] if len(sys.argv) > 2 else MAC_FILE)
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "candidates.json")
