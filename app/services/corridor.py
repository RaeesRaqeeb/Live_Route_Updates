# app/services/corridor.py
CORRIDORS = {
    "KKH": {"thakot", "besham", "dasu", "chilas", "jaglot", "gilgit",
            "hunza", "skardu", "karakoram", "astore", "northern", "kkh"},
    # add other known corridors (Fairy Meadows spur, Skardu-Khaplu, etc.)
}
# app/services/corridor.py
def is_relevant_post(content: str, origin: str, destination: str, corridor: str | None) -> bool:
    text = content.lower()
    terms = {origin.lower(), destination.lower()}
    if corridor:
        terms |= CORRIDORS.get(corridor, set())
    return any(term in text for term in terms if term)

def get_corridor(origin: str, destination: str) -> str | None:
    o, d = origin.lower(), destination.lower()
    for corridor, keywords in CORRIDORS.items():
        if any(kw in o for kw in keywords) or any(kw in d for kw in keywords):
            return corridor
    return None