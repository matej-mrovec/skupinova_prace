# Vestavěné knihovny
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime

# Externí knihovny
from rich.console import Console
from rich.table import Table

# Vytvoření objektu console pro barevné výpisy textu do konzole
console = Console()

# Konstantní proměnné
FORMAT_CASU = "%Y-%m-%d %H:%M"
SLOUPCE = ["Číslo čipu", "Zaměstnanec", "Příchod", "Odchod", "Hodiny"]


def nacti_data(dochazka_csv):
    # Načte platné řádky CSV a doplní délku směny v hodinách.
    zaznamy = []

    with open(dochazka_csv, "r", encoding="utf-8-sig", newline="") as soubor:
        ctecka = csv.DictReader(soubor, delimiter=";")

        if not ctecka.fieldnames:
            raise ValueError("CSV neobsahuje záhlaví.")

        # Normalizace názvů sloupců
        hlavicky = {
            nazev.strip().lower(): nazev
            for nazev in ctecka.fieldnames
            if nazev
        }

        pozadovane = {"číslo čipu", "zaměstnanec", "příchod", "odchod"}

        if not pozadovane.issubset(hlavicky):
            raise ValueError(
                "CSV musí obsahovat sloupce: "
                "číslo čipu;zaměstnanec;příchod;odchod"
            )

        for cislo, radek in enumerate(ctecka, start=2):
            try:
                prichod_text = radek[hlavicky["příchod"]].strip()
                odchod_text = radek[hlavicky["odchod"]].strip()

                if not prichod_text or not odchod_text:
                    raise ValueError("Chybí datum příchodu nebo odchodu.")

                prichod = datetime.strptime(prichod_text, FORMAT_CASU)
                odchod = datetime.strptime(odchod_text, FORMAT_CASU)

                if odchod < prichod:
                    raise ValueError("Odchod je před příchodem.")

                cislo_cipu = (radek[hlavicky["číslo čipu"]] or "").strip()
                zamestnanec = (radek[hlavicky["zaměstnanec"]] or "").strip()

                if not cislo_cipu or not zamestnanec:
                    raise ValueError("Chybí číslo čipu nebo jméno zaměstnance.")

                zaznamy.append({
                    "číslo čipu": cislo_cipu,
                    "zaměstnanec": zamestnanec,
                    "příchod": prichod,
                    "odchod": odchod,
                    "hodiny": round(
                        (odchod - prichod).total_seconds() / 3600, 2
                    ),
                })

            except (ValueError, TypeError, KeyError, AttributeError) as chyba:
                console.print(
                    f"[bold yellow]"
                    f"Upozornění: řádek {cislo} přeskočen ({chyba})."
                    f"[/bold yellow]"
                )

    return zaznamy


def seskup_zamestnance(zaznamy):
    # Vrátí souhrn hodin a směn pro každého zaměstnance.
    souhrn = defaultdict(
        lambda: {
            "číslo čipu": "",
            "počet_směn": 0,
            "celkem_hodin": 0.0
        }
    )

    for zaznam in zaznamy:
        jmeno = zaznam["zaměstnanec"]
        souhrn[jmeno]["číslo čipu"] = zaznam["číslo čipu"]
        souhrn[jmeno]["počet_směn"] += 1
        souhrn[jmeno]["celkem_hodin"] += zaznam["hodiny"]

    vysledek = []

    for jmeno, udaje in souhrn.items():
        udaje["zaměstnanec"] = jmeno
        udaje["celkem_hodin"] = round(udaje["celkem_hodin"], 2)
        udaje["průměrná_směna"] = round(
            udaje["celkem_hodin"] / udaje["počet_směn"], 2
        )
        vysledek.append(udaje)

    return sorted(
        vysledek,
        key=lambda x: x["celkem_hodin"],
        reverse=True
    )


def zobraz_souhrn(zaznamy):
    # Zobrazí souhrn zaměstnanců a extrémy směn pomocí tabulky.
    if not zaznamy:
        console.print("[bold red]Žádná data.[/bold red]")
        return

    souhrn = seskup_zamestnance(zaznamy)

    table = Table(title="SOUHRN ZAMĚSTNANCŮ")
    table.add_column("Zaměstnanec", justify="left")
    table.add_column("Číslo čipu", justify="right")
    table.add_column("Počet směn", justify="right")
    table.add_column("Celkem hodin", justify="right")
    table.add_column("Průměrná směna", justify="right")

    for osoba in souhrn:
        table.add_row(
            osoba["zaměstnanec"],
            osoba["číslo čipu"],
            str(osoba["počet_směn"]),
            f"{osoba['celkem_hodin']:.2f} h",
            f"{osoba['průměrná_směna']:.2f} h",
        )

    console.print(table)

    nejkratsi = min(zaznamy, key=lambda x: x["hodiny"])
    nejdelsi = max(zaznamy, key=lambda x: x["hodiny"])

    console.print(
        f"\n[bold]Nejkratší směna:[/bold] "
        f"{nejkratsi['zaměstnanec']} "
        f"({nejkratsi['příchod']:%Y-%m-%d %H:%M} - "
        f"{nejkratsi['odchod']:%H:%M}) | "
        f"[green]{nejkratsi['hodiny']:.2f} h[/green]"
    )

    console.print(
        f"[bold]Nejdelší směna:[/bold] "
        f"{nejdelsi['zaměstnanec']} "
        f"({nejdelsi['příchod']:%Y-%m-%d %H:%M} - "
        f"{nejdelsi['odchod']:%H:%M}) | "
        f"[green]{nejdelsi['hodiny']:.2f} h[/green]"
    )


def vytvor_tabulku_zaznamu(nalezene, titul="Záznamy"):
    table = Table(title=titul)
    table.add_column("Zaměstnanec", justify="left")
    table.add_column("Číslo čipu", justify="right")
    table.add_column("Příchod", justify="left")
    table.add_column("Odchod", justify="left")
    table.add_column("Hodiny", justify="right")

    for zaznam in nalezene:
        table.add_row(
            zaznam["zaměstnanec"],
            zaznam["číslo čipu"],
            zaznam["příchod"].strftime(FORMAT_CASU),
            zaznam["odchod"].strftime("%H:%M"),
            f"{zaznam['hodiny']:.2f} h",
        )

    return table


def hledej(zaznamy):
    # Vyhledá záznamy podle jména nebo čísla čipu.
    hledany = input("Zadejte jméno nebo číslo čipu: ").strip().lower()

    if not hledany:
        console.print("[yellow]Zadejte hledaný výraz.[/yellow]")
        return

    nalezene = [
        z for z in zaznamy
        if hledany in z["zaměstnanec"].lower()
        or hledany in z["číslo čipu"].lower()
    ]

    console.print(f"[bold]Nalezeno záznamů: {len(nalezene)}[/bold]")

    if nalezene:
        table = vytvor_tabulku_zaznamu(
            nalezene,
            titul=f"Výsledky hledání: '{hledany}'"
        )
        console.print(table)


def filtruj_den(zaznamy):
    # Filtruje a vypíše příchody pro zadané datum.
    den = input("Zadejte datum (YYYY-MM-DD): ").strip()

    try:
        datetime.strptime(den, "%Y-%m-%d")
    except ValueError:
        console.print(
            "[bold red]Neplatný formát data. Použijte YYYY-MM-DD.[/bold red]"
        )
        return

    nalezene = [
        z for z in zaznamy
        if z["příchod"].strftime("%Y-%m-%d") == den
    ]

    nalezene.sort(key=lambda z: z["příchod"])

    if nalezene:
        table = vytvor_tabulku_zaznamu(
            nalezene,
            titul=f"Příchody dne {den}"
        )
        console.print(table)
    else:
        console.print(
            "[yellow]Pro tento den nebyly nalezeny žádné záznamy.[/yellow]"
        )


def zobraz_upozorneni(zaznamy):
    # Upozorní na neobvykle krátké směny nebo pozdní příchody.
    podezrele = [
        z for z in zaznamy
        if z["hodiny"] < 4 or z["příchod"].hour >= 9
    ]

    console.print(
        "\n[bold red]UPOZORNĚNÍ "
        "(směna kratší než 4 h nebo příchod v 9:00 a později)[/bold red]"
    )

    if not podezrele:
        console.print("[green]Žádné neobvyklé směny.[/green]")
        return

    table = vytvor_tabulku_zaznamu(
        podezrele,
        titul="Podezřelé směny"
    )
    console.print(table)


def uloz_json(data, nazev_souboru):
    try:
        with open(
            nazev_souboru,
            "w",
            encoding="utf-8",
            newline=""
        ) as soubor:
            json.dump(
                data,
                soubor,
                indent=4,
                ensure_ascii=False
            )

        console.print(
            f"[bold green]Data byla uložena do {nazev_souboru}[/bold green]"
        )

    except (OSError, TypeError, ValueError) as error:
        console.print(
            f"[bold red]Chyba při ukládání JSON: {error}[/bold red]"
        )


def exportuj_json(zaznamy):
    cesta = (
        input("Název JSON souboru (Enter = vysledek.json): ").strip()
        or "vysledek.json"
    )

    souhrn = seskup_zamestnance(zaznamy)
    uloz_json(souhrn, cesta)


def menu():
    console.print()
    console.rule("[bold blue]ANALÝZA DOCHÁZKY[/bold blue]")
    console.print()
    console.print("1 - Souhrn zaměstnanců")
    console.print("2 - Hledat podle jména nebo čipu")
    console.print("3 - Zobrazit příchody vybraného dne")
    console.print("4 - Neobvyklé směny a pozdní příchody")
    console.print("5 - Export souhrnu do JSON")
    console.print("0 - Ukončení aplikace")


def main():
    if len(sys.argv) != 2:
        console.print(
            "[bold red]Použití: python main.py dochazka.csv[/bold red]"
        )
        return

    try:
        zaznamy = nacti_data(sys.argv[1])

        console.print(
            f"[green]Načteno záznamů: {len(zaznamy)}[/green]"
        )

        while True:
            menu()
            volba = input("\nVolba: ").strip()

            if volba == "1":
                zobraz_souhrn(zaznamy)

            elif volba == "2":
                hledej(zaznamy)

            elif volba == "3":
                filtruj_den(zaznamy)

            elif volba == "4":
                zobraz_upozorneni(zaznamy)

            elif volba == "5":
                exportuj_json(zaznamy)

            elif volba == "0":
                console.print("[bold]Nashledanou.[/bold]")
                break

            else:
                console.print("[red]Neplatná volba.[/red]")

    except (FileNotFoundError, OSError, ValueError) as chyba:
        console.print(
            f"[bold red]Chyba: {chyba}[/bold red]"
        )


if __name__ == "__main__":
    main()
