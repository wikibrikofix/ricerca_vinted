"""
Analisi qualita' di un annuncio a partire da titolo + descrizione.

Approccio a regole (trasparente, senza dipendenze esterne / LLM):
- Cerca segnali POSITIVI e NEGATIVI (parole chiave pesate) nel testo.
- Calcola un punteggio 0-100 e un giudizio sintetico.
- Estrae "commenti del venditore" rilevanti: difetti dichiarati, accessori
  inclusi, ore d'uso, garanzia, motivo di vendita, ecc.

Le keyword coprono italiano/francese/inglese/spagnolo (Vinted e' multilingua).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Segnali positivi -> (peso, regex)
POSITIVE = [
    (3, r"\b(perfettamente funzionante|perfetto stato|come nuovo|comme neuf|like new|impeccabl\w*|nickel|ottimo stato|ottime condizioni)\b"),
    (2, r"\b(funziona(nte)?|fonctionne|works?|funciona|testato|tested|testé|collaudato)\b"),
    (2, r"\b(scatola originale|imballo originale|boite d'origine|original box|fattura|ricevuta|garanzia|garantie|warranty)\b"),
    (2, r"\b(mai usato|jamais utilisé|never used|nuovo|neuf|new|sigillat\w+|scellé|sealed|precintado)\b"),
    (1, r"\b(pulit\w+|propre|clean|accessori inclusi|accessoires|completo di|con scatola)\b"),
]
# Segnali negativi -> (peso, regex)
NEGATIVE = [
    (3, r"\b(non funziona|ne fonctionne pas|not working|no funciona|guasto|rotto|cassé|broken|difettos\w+|per ricambi|for parts|pour pièces)\b"),
    (2, r"\b(difett\w+|défaut|defect|problema|problème|issue|graffi\w*|rayure|scratch|ammaccat\w+|rott\w+|usurat\w+|worn)\b"),
    (2, r"\b(senza (disch|hard|hdd|alimentatore|cavo)|sans (disque|câble|alimentation)|no (disk|hdd|cable|psu)|manca\b|manque|missing)\b"),
    (2, r"\b\d{1,3}[.\s]?\d{3}\s*(ore|heures|hours)\b"),  # molte ore d'uso (con separatore migliaia)
    (1, r"\b(usat\w+|used|usé|usado|segni d'uso|traces d'usage|signs of (use|wear))\b"),
]

# Estrazione "commenti/dettagli" del venditore
DETAIL_PATTERNS = {
    "difetti_dichiarati": r"[^.]*\b(difett\w+|défaut|graffi\w*|rayure|scratch|non funziona|guasto|rotto|problema|manca\b|manque)\b[^.]*\.",
    "accessori_inclusi": r"[^.]*\b(inclus\w*|incluso|allego|regalo|con scatola|scatola originale|alimentatore|cavo|accessoir\w+|avec)\b[^.]*\.",
    "ore_uso": r"\b\d{1,3}[.\s]?\d{2,3}\s*(ore|heures|hours|h)\b",
    "garanzia": r"[^.]*\b(garanzia|garantie|warranty|fattura|ricevuta|facture)\b[^.]*\.",
    "motivo_vendita": r"[^.]*\b(vendo per|vendo perché|cause|car je|because|passo a|cambio con|upgrade)\b[^.]*\.",
}


@dataclass
class QualityReport:
    score: int                       # 0-100
    verdict: str                     # es. "Buono", "Attenzione"
    positives: list = field(default_factory=list)
    negatives: list = field(default_factory=list)
    seller_notes: dict = field(default_factory=dict)
    condition: Optional[str] = None


def _find(patterns, text):
    hits = []
    for weight, pat in patterns:
        for m in re.finditer(pat, text, re.I):
            hits.append((weight, m.group(0).strip()))
    return hits


def analyze(title: str, description: str = "", condition: str = None) -> QualityReport:
    """Analizza titolo+descrizione e ritorna un QualityReport."""
    text = f"{title or ''}. {description or ''}"
    pos = _find(POSITIVE, text)
    neg = _find(NEGATIVE, text)

    # punteggio base 55 (neutro), modulato dai segnali e dalla condizione dichiarata
    score = 55 + sum(w for w, _ in pos) * 5 - sum(w for w, _ in neg) * 6
    cond_bonus = {
        "nuovo con cartellino": 20, "nuovo senza cartellino": 15,
        "ottime": 10, "ottimo": 10, "buone": 0, "buono": 0,
        "discrete": -12, "discreto": -12, "soddisfacenti": -18,
    }
    if condition:
        for k, v in cond_bonus.items():
            if k in condition.lower():
                score += v
                break
    # penalita' se non c'e' descrizione (poca trasparenza del venditore)
    if not description or len(description.strip()) < 15:
        score -= 5
    score = max(0, min(100, score))

    if score >= 75:
        verdict = "Ottimo"
    elif score >= 60:
        verdict = "Buono"
    elif score >= 45:
        verdict = "Discreto"
    else:
        verdict = "Attenzione"

    # dettagli/commenti venditore
    notes = {}
    for name, pat in DETAIL_PATTERNS.items():
        found = [m.group(0).strip() for m in re.finditer(pat, text, re.I)]
        if found:
            # dedup mantenendo ordine
            seen = []
            for f in found:
                if f not in seen:
                    seen.append(f)
            notes[name] = seen[:3]

    return QualityReport(
        score=score, verdict=verdict,
        positives=[h for _, h in pos], negatives=[h for _, h in neg],
        seller_notes=notes, condition=condition,
    )


def analyze_item(item) -> QualityReport:
    """Comodo: analizza un Item (usa title, description, condition)."""
    return analyze(item.title, item.description or "", item.condition)
