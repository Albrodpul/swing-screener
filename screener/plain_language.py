"""Traducción a lenguaje plano. Cero jerga técnica.

Convierte motivos del screener (RS, breakout, ATR, blow-off...) a frases que entiende
cualquier persona sin formación bursátil. El texto es PERSONAL por empresa: se construye
a partir de los motivos reales que tiene cada una (sus entry_reasons / blockers / exits
concretos), no de una plantilla fija, y usa el nombre de la empresa.
"""
from __future__ import annotations
import re
from typing import Any
import numpy as np
import pandas as pd


SIGNAL_SHORT = {
    "COMPRA":    ("Comprar hoy",    "🟢"),
    "OBSERVAR":  ("Vigilar",        "👀"),
    "EVITAR":    ("Saltar",         "⚪"),
    "SALIDA":    ("Vender",         "🔴"),
    "INELIGIBLE": ("Saltar",        "⛔"),
}

# Sufijos legales/societarios que quitamos para un nombre coloquial
_NAME_SUFFIXES = {
    "inc", "inc.", "incorporated", "corp", "corp.", "corporation", "co", "co.",
    "company", "ltd", "ltd.", "limited", "plc", "llc", "lp", "holdings", "holding",
    "group", "ord", "ag", "se", "sa", "s.a.", "nv", "n.v.", "spa", "ab", "asa",
    "oyj", "the", "class", "&",
}


def _as_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _has(lst: list, needle: str) -> bool:
    return any(needle.lower() in str(x).lower() for x in lst)


def _find(lst: list, needle: str) -> str | None:
    """Devuelve el primer elemento que contiene needle (para extraer números)."""
    for x in lst:
        if needle.lower() in str(x).lower():
            return str(x)
    return None


def _short_name(name: str | None) -> str:
    """Nombre coloquial: 'NVIDIA Corporation' -> 'NVIDIA'. Fallback: 'la empresa'."""
    if not name or not str(name).strip():
        return "la empresa"
    raw = str(name).replace(",", " ").strip()
    tokens = raw.split()
    # quita sufijos legales del final
    while tokens and tokens[-1].lower().strip(".") in {s.strip(".") for s in _NAME_SUFFIXES}:
        tokens.pop()
    if not tokens:
        return str(name).strip()
    # como mucho 3 palabras, para que sea corto y natural
    short = " ".join(tokens[:3])
    return short


def _strength_phrase(rs: float) -> str:
    if rs >= 95: return f"está entre el {max(1, round(100-rs))}% de empresas que más suben de todo el mercado"
    if rs >= 85: return f"sube más rápido que el {rs:.0f}% del mercado"
    if rs >= 70: return f"va por delante del {rs:.0f}% del mercado"
    if rs >= 50: return "se mueve parecido al promedio del mercado"
    return f"se está comportando peor que el {max(1, round(100-rs))}% del mercado"


def _sector_phrase(theme: float | None) -> str:
    if theme is None: return ""
    if theme >= 80: return "Y su sector es ahora mismo de los más fuertes del mercado, lo que empuja a favor."
    if theme >= 60: return "Su sector acompaña, con viento a favor."
    if theme <= 30: return "En contra juega que su sector está flojo."
    return ""


def _volume_x(entry_reasons: list) -> str:
    """Extrae el 'N×' del motivo de breakout, o frase genérica."""
    br = _find(entry_reasons, "Breakout sobre pivot")
    if br:
        m = re.search(r"([\d.,]+)\s*[×x]", br)
        if m:
            return f"{m.group(1)}× lo normal"
    return "por encima de lo normal"


def _strength_clauses(r: dict, rs: float, entry_reasons: list) -> list[str]:
    """Frases de fuerza/calidad que SÍ tiene esta empresa, en orden natural."""
    out = []
    if _has(entry_reasons, "Breakout sobre pivot"):
        out.append(f"acaba de romper al alza con un volumen de compra {_volume_x(entry_reasons)} "
                   "(dinero real entrando, no un amago)")
    if rs and rs >= 70:
        out.append(_strength_phrase(rs))
    if _has(entry_reasons, "Línea de fuerza relativa en máximos"):
        out.append("su fuerza frente al mercado está en máximos: lidera, no va a remolque")
    elif _has(entry_reasons, "mejorando últimas 4 semanas"):
        out.append("y va ganando fuerza semana a semana")
    if _has(entry_reasons, "tendencia alcista"):
        out.append("su tendencia de fondo lleva tiempo siendo alcista y ordenada")
    return out


def _join_natural(clauses: list[str]) -> str:
    """Une frases con comas y 'además' para que no suene a lista."""
    clauses = [c for c in clauses if c]
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0].capitalize() + "."
    if len(clauses) == 2:
        return f"{clauses[0].capitalize()}, y {clauses[1]}."
    head = clauses[0].capitalize()
    mid = ", ".join(clauses[1:-1])
    return f"{head}. Además {mid}, y {clauses[-1]}."


def _exit_clause(reason: str, name: str, pct: float, rs: float) -> str:
    """Frase plana para un motivo de salida concreto."""
    rl = reason.lower()
    if "blow-off" in rl:
        return (f"{name} ha subido demasiado y demasiado rápido: está un {pct:.0f}% por encima de su media reciente. "
                "Históricamente, cuando una acción se estira tanto, lo que suele venir después es una corrección fuerte. "
                "Si la tienes con ganancias, es razonable proteger beneficios; si no la tienes, no entres aquí.")
    if "stop atr" in rl:
        return (f"El precio de {name} ha caído por debajo del nivel que considerábamos seguro. "
                "Suele indicar que los compradores se retiran y mandan los vendedores. "
                "Si la tienes, lo prudente es cerrar y proteger lo ganado; ya habrá tiempo de volver si se recupera.")
    if "pérdida de sma50" in rl or "perdida de sma50" in rl:
        return (f"{name} ha perdido una referencia clave (su media de los últimos 50 días) varios días seguidos y con volumen. "
                "Es un primer aviso serio de que la tendencia se está girando. Si la tienes, vigílala muy de cerca.")
    if "fuerza relativa rompiendo" in rl:
        base = f"{name} está perdiendo fuelle frente al resto del mercado: lleva varios días haciéndolo peor que el promedio. "
        if rs and rs >= 60:
            return base + "Aún tiene fuerza, pero ya no lidera. Si la tienes, no es urgente vender, pero si sigue así otra semana, mejor salir."
        return base + "Y su fuerza ya no es alta, así que no hay razón para esperar un giro. Si la tienes, plantéate cerrar."
    if "rotación sectorial" in rl or "rotacion sectorial" in rl:
        return (f"El sector entero de {name} está perdiendo fuelle frente al mercado. "
                "Cuando un sector flojea, las empresas de dentro suelen seguir el mismo camino aunque parezcan sólidas. "
                "El viento que la empujaba ya no sopla.")
    if "distribución institucional" in rl or "distribucion institucional" in rl:
        return (f"En {name} se está vendiendo más de lo que se compra en las últimas semanas: "
                "los grandes inversores parecen estar soltando papel poco a poco. Mala señal de fondo.")
    if "mercado en distribución" in rl or "mercado en distribucion" in rl:
        return ("El mercado en general está vendiendo de forma consistente estos días. "
                "En estas fases casi nada funciona y los rebotes suelen fallar; mejor reducir riesgo y esperar a que se calme.")
    if "deterioro fundamental" in rl:
        return (f"Los números de {name} empeoran trimestre a trimestre (ventas o beneficios cayendo de forma sostenida). "
                "El problema no es solo el gráfico, es el negocio.")
    return f"{name} tiene una señal de aviso activa. Si la tienes, conviene revisarla de cerca."


def humanize(row: pd.Series | dict) -> str:
    """Devuelve párrafo plano, argumentado y PERSONAL para esta empresa."""
    r = row if isinstance(row, dict) else row.to_dict()
    sig = r.get("signal", "OBSERVAR")
    name = _short_name(r.get("name"))
    entry_reasons = _as_list(r.get("entry_reasons"))
    exits = _as_list(r.get("exit_reasons"))
    blockers = _as_list(r.get("entry_blockers"))
    pct = (r.get("pct_above_sma50") or 0) * 100
    rs = r.get("rs_rating") or 0
    theme = r.get("theme_score")
    fscore = r.get("f_score") or 0
    sector_p = _sector_phrase(theme)

    # ── COMPRA ──────────────────────────────────────────────────────────────
    if sig == "COMPRA":
        body = _join_natural(_strength_clauses(r, rs, entry_reasons))
        parts = [f"**{name} es una buena entrada hoy.**"]
        if body:
            parts.append(body)
        if r.get("not_extended") or _has(entry_reasons, "No extendida"):
            parts.append(f"Y no llegas tarde: el precio está solo un {pct:.0f}% sobre su media reciente, "
                         "así que entras con margen en vez de persiguiendo una subida ya hecha.")
        if sector_p:
            parts.append(sector_p)
        if fscore >= 6:
            parts.append(f"Para rematar, las cuentas de la empresa son sólidas ({fscore} de 9 en salud financiera).")
        return " ".join(parts)

    # ── INELIGIBLE ──────────────────────────────────────────────────────────
    if sig == "INELIGIBLE":
        return (f"**{name} no pasa el filtro de calidad.** Sus cuentas están flojas "
                f"({fscore} de 9 en salud financiera), así que aunque el precio se anime, "
                "el riesgo de fondo es alto. Mejor saltarla y buscar otra más sólida.")

    # ── SALIDA ──────────────────────────────────────────────────────────────
    if sig == "SALIDA":
        # prioridad: lo más grave primero
        priority = ["blow-off", "Stop ATR", "Pérdida de SMA50", "Fuerza relativa rompiendo",
                    "Rotación sectorial", "Distribución institucional", "Mercado en distribución",
                    "Deterioro fundamental"]
        chosen = None
        for key in priority:
            m = _find(exits, key)
            if m:
                chosen = m
                break
        if chosen is None and exits:
            chosen = str(exits[0])
        lead = _exit_clause(chosen, name, pct, rs) if chosen else \
            f"{name} tiene señales de aviso activas. Si la tienes, revísala de cerca."
        text = f"**Señal de venta en {name}.** " + lead
        # si además era líder fuerte, matiz
        otros = [e for e in exits if e != chosen]
        if len(otros) >= 1 and "mercado en distribución" not in (chosen or "").lower():
            text += " Y no es la única señal en contra: hay más de un aviso a la vez, lo que refuerza la cautela."
        return text

    # ── EVITAR ──────────────────────────────────────────────────────────────
    if sig == "EVITAR":
        if _has(blockers, "Demasiado extendida"):
            msg = (f"**{name} es fuerte, pero hoy está a mal precio.** "
                   f"Ha subido un {pct:.0f}% sobre su media reciente — comprar aquí es perseguir el precio. ")
            if exits:
                msg += "Encima tiene alguna señal de aviso activa que añade riesgo. "
            msg += "Si te interesa, ponla en seguimiento y espera a que corrija un 10-15% antes de entrar."
            return msg
        if rs and rs >= 70:
            return (f"**Hoy no es momento de entrar en {name}.** "
                    f"Tiene fuerza ({_strength_phrase(rs)}), pero hay avisos activos (de mercado, sector o de ella misma) "
                    "que hoy pesan más que su potencial. Mejor mirar otras oportunidades o esperar a que se despejen.")
        return (f"**Hoy no es momento de entrar en {name}.** "
                "Tiene avisos activos que sugieren que el riesgo supera al potencial. Mejor buscar otra mejor.")

    # ── OBSERVAR ────────────────────────────────────────────────────────────
    # Empresa que no dispara COMPRA por un motivo concreto. Personalizamos según el bloqueador.
    strengths = _strength_clauses(r, rs, entry_reasons)

    if _has(blockers, "Demasiado extendida"):
        msg = (f"**{name} es muy fuerte, pero ya viene muy subida.** "
               f"{_strength_phrase(rs).capitalize()}, lo cual es excelente. "
               f"El problema: ha subido un {pct:.0f}% sobre su media reciente, así que comprar hoy es pagar caro. ")
        if sector_p:
            msg += sector_p + " "
        msg += ("**Qué hacer**: ponla en seguimiento. Si en las próximas semanas corrige un 10-15% "
                "(acercándose a su media), ese retroceso puede ser tu entrada con riesgo controlado.")
        return msg

    if _has(blockers, "Sin breakout"):
        if rs and rs >= 70:
            arranque = f"**{name} está casi lista, pero el precio aún espera.** La fuerza está ahí ({_strength_phrase(rs)}) y la tendencia acompaña, "
        else:
            arranque = f"**{name} tiene buena tendencia, pero el precio aún espera.** De momento {_strength_phrase(rs)}, "
        msg = (arranque +
               "pero todavía no hay disparador: el precio está consolidando, sin romper hacia arriba. ")
        if sector_p:
            msg += sector_p + " "
        msg += ("**Qué hacer**: vigílala. El día que rompa al alza con volumen de compra real, ese es el momento de entrar.")
        return msg

    if _has(blockers, "Breakout sin confirmación"):
        return (f"**{name} sube hoy, pero sin convicción.** "
                "Ha intentado romper hacia arriba y la gente no se ha animado a comprar de verdad: el volumen es bajo. "
                "Sin compradores empujando, estos amagos suelen fallar y el precio vuelve atrás. "
                "**Qué hacer**: esperar a que rompa otro día, esta vez con volumen alto, antes de entrar.")

    if _has(blockers, "Fuerza relativa insuficiente"):
        return (f"**{name} todavía no destaca frente al mercado.** "
                f"De momento {_strength_phrase(rs)}, así que no hay razón para preferirla a otras más fuertes. "
                "Si te gusta a largo plazo, espérala: cuando empiece a liderar se notará en los rankings y tendrás margen para entrar.")

    if _has(blockers, "Medias") or _has(blockers, "SMA") or _has(blockers, "Lejos del máximo") or _has(blockers, "Precio por debajo"):
        return (f"**La tendencia de fondo de {name} aún no es claramente alcista.** "
                "Aunque la empresa pueda gustar, el gráfico dice que todavía no está en posición de subir con continuidad. "
                "**Qué hacer**: esperar a que construya una base sólida y gire al alza antes de entrar.")

    # OBSERVAR sin bloqueador identificado
    base = f"**{name} está en seguimiento.** "
    if strengths:
        base += _join_natural(strengths[:2]) + " "
        base += "Hoy no hay un disparador claro de compra, pero merece estar en la lista: vigílala por si rompe al alza."
    else:
        base += "Hoy no hay un disparador claro, pero la empresa merece estar en la lista de seguimiento."
    return base


def humanize_card(row: pd.Series | dict) -> dict:
    """Devuelve dict con campos listos para pintar en UI plana."""
    r = row if isinstance(row, dict) else row.to_dict()
    sig = r.get("signal", "OBSERVAR")
    label, emoji = SIGNAL_SHORT.get(sig, (sig, ""))

    fund = r.get("fund_composite")
    rs = r.get("rs_rating")
    # Métrica unificada 0-100: media ponderada calidad+fuerza
    fuerza = None
    if fund is not None and rs is not None:
        fuerza = float(0.5 * fund + 0.5 * rs)

    return {
        "ticker": r.get("ticker"),
        "sector": r.get("sector") or "—",
        "signal": sig,
        "label": label,
        "emoji": emoji,
        "precio": r.get("close"),
        "fuerza": fuerza,             # 0-100, mezcla salud + ímpetu
        "calidad": fund,              # fundamentales+temas
        "impulso": rs,                # fuerza vs mercado
        "explicacion": humanize(r),
        # técnicos para "ver más detalle"
        "tecnico": {
            "rs_rating": rs,
            "trend_template": r.get("trend_template"),
            "breakout": r.get("breakout"),
            "volume_ok": r.get("volume_ok"),
            "exit_active": r.get("exit_active"),
            "f_score": r.get("f_score"),
            "qv_score": r.get("qv_score"),
            "fi_score": r.get("fi_score"),
            "theme_score": r.get("theme_score"),
            "pct_above_sma50": r.get("pct_above_sma50"),
            "entry_reasons": _as_list(r.get("entry_reasons")),
            "entry_blockers": _as_list(r.get("entry_blockers")),
            "exit_reasons": _as_list(r.get("exit_reasons")),
        },
    }
