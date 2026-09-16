# Ricerca Vinted

Scraper del catalogo [Vinted](https://www.vinted.it) basato su un **browser reale**
(Playwright/Chromium), con analisi dei risultati tramite pandas.

Sviluppato per fare ricerche di mercato personali (es. confrontare prezzi e modelli
di prodotti usati) estraendo i dati direttamente dalle pagine del catalogo.

## Perché Playwright e non l'API

L'endpoint JSON di Vinted (`/api/v2/catalog/items`) è protetto da **Datadome**
(sistema anti-bot). Le chiamate programmatiche dirette vengono bloccate:

| Approccio | Risultato |
|-----------|-----------|
| `requests` / `httpx` + cookie di sessione | 404 (pagina di errore mascherata) |
| `curl-cffi` con fingerprint TLS di Chrome | 404 |
| **Browser reale (Playwright)** | ✅ carica il catalogo |

Il motivo: il blocco dipende dalla reputazione dell'IP e dalla sfida JavaScript di
Datadome, che solo un browser vero (che esegue JS) supera. Da qui la scelta di
guidare un Chromium reale ed estrarre i dati dal **DOM** invece che dall'API.

## Come vengono estratti i dati

Ogni card annuncio espone un link con un attributo `title` già strutturato:

```
"Maglia Nike, Brand: Nike, Condizioni: Ottime, Taglia: M, 15.00 €, 16.45 €"
```

Da cui ricaviamo: `title`, `brand`, `condition`, `size`, `price`, `total_price`.
L'`id` dell'annuncio viene dall'URL `/items/<id>`.

## Installazione

```bash
# 1. crea un ambiente virtuale
python3 -m venv .venv
source .venv/bin/activate

# 2. installa le dipendenze
pip install -r requirements.txt

# 3. installa il browser Chromium per Playwright
playwright install chromium
```

In alternativa, installazione come pacchetto (fornisce il comando `ricerca-vinted`):

```bash
pip install -e .
playwright install chromium
```

## Uso — riga di comando

```bash
# ricerca base (2 pagine)
python -m ricerca_vinted.cli "sneakers nike"

# più pagine + esporta CSV
python -m ricerca_vinted.cli "nas synology" --pages 3 --csv risultati.csv

# filtra per categoria (alias 'computer' = Elettronica > Computer, id 2994)
python -m ricerca_vinted.cli "nas" --catalog computer --pages 2

# altro dominio Vinted
python -m ricerca_vinted.cli "veste" --base https://www.vinted.fr --locale fr-FR

# mostra il browser (debug)
python -m ricerca_vinted.cli "drobo" --show
```

Se installato come pacchetto, usa direttamente `ricerca-vinted "query" ...`.

### Opzioni

| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `query` | testo di ricerca (posizionale) | — |
| `--base` | dominio Vinted | `https://www.vinted.it` |
| `--pages` | numero di pagine da scorrere | `2` |
| `--catalog` | ID categoria o alias (`computer`) | nessuno |
| `--pause` | secondi di pausa tra pagine (+ jitter) | `1.5` |
| `--csv` | salva i dati grezzi in CSV | — |
| `--show` | mostra il browser (non headless) | headless |
| `--locale` | locale del browser | `it-IT` |

## Uso — come libreria

```python
from ricerca_vinted import VintedScraper
from ricerca_vinted.analysis import items_to_dataframe, summarize

scraper = VintedScraper(base="https://www.vinted.it")
items = scraper.search("nas synology", pages=2, catalog="2994")

df = items_to_dataframe(items)
print(summarize(df))

for it in items[:5]:
    print(it.id, it.title, it.price, it.url)
```

## Esempio: ricerca NAS

`examples/nas_finder.py` cerca NAS su più marchi nella categoria Computer e
classifica i modelli 2-bay per idoneità (RAID 1 + Amazon S3, e file system Btrfs
per l'integrità del dato):

```bash
python examples/nas_finder.py --pages 2 --max-price 100
```

## Struttura del progetto

```
ricerca_vinted/
├── ricerca_vinted/
│   ├── __init__.py       # API pubblica
│   ├── scraper.py        # VintedScraper, Item, parse_title
│   ├── analysis.py       # items_to_dataframe, summarize
│   └── cli.py            # interfaccia a riga di comando
├── examples/
│   └── nas_finder.py     # esempio ricerca/filtro NAS
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Categorie note (dominio .it)

| Alias | ID | Categoria |
|-------|----|-----------|
| `computer` | `2994` | Elettronica → Computer e informatica |

Per trovare altri ID: apri la categoria sul sito e leggi il numero nell'URL
(`/catalog/<id>-<slug>`).

## Manutenzione

Il layout di Vinted può cambiare. Se l'estrazione si svuota:

1. Verifica che le etichette in `LABELS` (`scraper.py`) corrispondano alla lingua
   del dominio (es. per `.fr`: `Marque:`, `État:`, `Taille:`).
2. Controlla che le card usino ancora `<a href="/items/...">` con attributo `title`.

### Nota sul nome del package

Il package Python si chiama `ricerca_vinted` (non `vinted_scraper`) proprio per
evitare conflitti con l'omonimo pacchetto PyPI `vinted_scraper` (basato sull'API,
non su Playwright), che ha un'interfaccia diversa. Import corretto:

```python
from ricerca_vinted import VintedScraper
```

## Note legali e uso responsabile

- **Solo uso personale.** Lo scraping automatizzato viola i Termini di Servizio di
  Vinted; la sanzione tipica è il ban dell'account.
- **Non raccogliere PII** (username, email, dati dei venditori).
- **Rispetta un rate ragionevole** (il default include pausa + jitter tra le pagine).
- **Non esporre né rivendere** i dati raccolti.

## Licenza

MIT.
