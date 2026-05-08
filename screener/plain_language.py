"""Traducción a lenguaje plano. Cero jerga técnica.

Convierte motivos del screener (RS, breakout, ATR, blow-off...) a frases que entiende
cualquier persona sin formación bursátil.
"""
from __future__ import annotations
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


def _strength_phrase(rs: float) -> str:
    if rs >= 95: return f"está entre el {100-rs:.0f}% de empresas que más suben de todo el mercado"
    if rs >= 85: return f"sube más rápido que el {rs:.0f}% del mercado"
    if rs >= 70: return f"está por encima del {rs:.0f}% del mercado en momento alcista"
    if rs >= 50: return "tiene un comportamiento similar al promedio del mercado"
    return f"se está comportando peor que el {100-rs:.0f}% del mercado"


def _sector_phrase(theme: float | None) -> str:
    if theme is None: return ""
    if theme >= 80: return "El sector al que pertenece está siendo de los más fuertes del mercado ahora mismo, lo que ayuda."
    if theme >= 60: return "El sector va bien, sopla viento a favor."
    if theme <= 30: return "El sector está flojo, lo que juega en contra."
    return ""


def humanize(row: pd.Series | dict) -> str:
    """Devuelve párrafo plano y argumentado para esta empresa."""
    r = row if isinstance(row, dict) else row.to_dict()
    sig = r.get("signal", "OBSERVAR")
    exits = _as_list(r.get("exit_reasons"))
    blockers = _as_list(r.get("entry_blockers"))
    pct = (r.get("pct_above_sma50") or 0) * 100
    rs = r.get("rs_rating") or 0
    theme = r.get("theme_score")
    fscore = r.get("f_score") or 0
    fi = r.get("fi_score") or 0
    qv = r.get("qv_score") or 0
    sector_p = _sector_phrase(theme)

    if sig == "COMPRA":
        parts = [
            f"**Hoy es un buen momento para entrar.** "
            f"El precio ha roto un techo importante y ha venido con fuerza compradora real, "
            f"no es un rebote tibio.",
            f"En cuanto a fuerza, la empresa {_strength_phrase(rs)}, lo cual indica que es de las que están "
            f"liderando el momento actual, no una rezagada.",
            f"La subida desde su media reciente es de un {pct:.0f}% — saludable: ni parada ni disparada, "
            f"que es justo donde suelen empezar los movimientos buenos.",
        ]
        if sector_p: parts.append(sector_p)
        if fscore >= 6:
            parts.append(f"Además, los números de la empresa son sólidos (puntuación financiera {fscore}/9).")
        return " ".join(parts)

    if sig == "INELIGIBLE":
        return (
            f"Los fundamentales de la empresa están flojos (puntuación financiera {fscore}/9). "
            "Aunque el precio se anime, el riesgo de fondo es alto. Mejor saltarla y buscar otra mejor."
        )

    if sig == "SALIDA":
        if _has(exits, "blow-off"):
            return (
                f"**Cuidado: la empresa ha subido demasiado, demasiado rápido.** "
                f"Está un {pct:.0f}% por encima de su media reciente — eso es muchísimo. "
                f"Históricamente, cuando una acción se aleja tanto y tan rápido, lo que viene después "
                f"suele ser una corrección importante (a veces del 20% o más). "
                f"Si la tienes y has ganado mucho, ahora es razonable bloquear beneficios. "
                f"Si no la tienes, no entres aquí: el riesgo no compensa."
            )
        if _has(exits, "Stop ATR"):
            return (
                "**El precio ha caído por debajo del nivel que considerábamos seguro.** "
                "Cuando esto pasa, suele indicar que los compradores se han retirado y los vendedores "
                "están tomando el control. Si tienes la posición, lo más prudente es cerrarla y proteger lo ganado "
                "(o limitar la pérdida). Si vuelve a recuperarse, ya habrá tiempo de volver a entrar; "
                "lo importante ahora es no quedarse mirando cómo cae más."
            )
        if _has(exits, "Fuerza relativa rompiendo"):
            base = (
                f"**La empresa está perdiendo fuelle frente al resto del mercado.** "
                f"Durante varios días seguidos lo está haciendo peor que el promedio. "
            )
            if rs >= 60:
                base += (
                    f"Aún tiene buena fuerza global ({_strength_phrase(rs)}), pero ya no lidera, "
                    "está cediendo terreno. Si la tienes, no es urgencia de venta inmediata, "
                    "pero conviene vigilar de cerca: si sigue así una semana más, mejor salir."
                )
            else:
                base += (
                    "Y su fuerza ya no es alta, así que no hay razón para mantenerla esperando un giro. "
                    "Si la tienes, plantéate cerrar."
                )
            return base
        if _has(exits, "Cierre por debajo"):
            return (
                "**Hoy ha caído con fuerza por debajo de un nivel clave, y además con mucha gente vendiendo.** "
                "Esa combinación (caída + volumen alto) suele ser el inicio de una corrección, no un susto pasajero. "
                "Si la tienes, plantéate salir hoy mismo."
            )
        if _has(exits, "Rotación sectorial"):
            return (
                "**El sector entero al que pertenece está perdiendo fuelle frente al mercado.** "
                "Cuando un sector empieza a flojear, las empresas dentro suelen seguir el mismo camino, "
                "incluso las que parecían sólidas individualmente. Si la tienes, vigílala — el viento "
                "que la empujaba ya no sopla."
            )
        if _has(exits, "Mercado en distribución"):
            return (
                "**El mercado en general está vendiendo de forma consistente.** "
                "En estas fases, casi nada funciona y los rebotes suelen fallar. "
                "Mejor reducir riesgo y esperar a que las aguas se calmen."
            )
        return "Hay varias señales de aviso activas. Si la tienes, conviene revisarla de cerca."

    if sig == "EVITAR":
        if _has(blockers, "Demasiado extendida"):
            return (
                f"**Es una empresa fuerte, pero ahora mismo está a un mal precio.** "
                f"Ha subido un {pct:.0f}% por encima de su media reciente — eso es mucho, "
                "y comprar aquí es perseguir el precio. "
                "Además hay alguna señal de aviso activa que añade riesgo. "
                "Si te interesa, ponla en seguimiento y espera a que corrija un 10-15% antes de entrar."
            )
        return (
            "**No es momento de entrar aquí.** "
            "La empresa tiene avisos activos (mercado, sector o ella misma) que sugieren que "
            "el riesgo supera al potencial hoy. Mejor mirar otras oportunidades."
        )

    # OBSERVAR
    if _has(blockers, "Demasiado extendida"):
        msg = (
            f"**Empresa muy fuerte pero ya muy subida.** "
            f"{_strength_phrase(rs).capitalize()}, lo que es excelente. "
            f"Pero ha subido un {pct:.0f}% sobre su media reciente, así que entrar hoy es comprar caro. "
        )
        if sector_p: msg += sector_p + " "
        msg += (
            "**Estrategia**: ponla en lista de seguimiento. Si en las próximas semanas baja un 10-15% "
            "(volviéndose a su media o cerca), ese retroceso puede ser tu entrada con riesgo controlado."
        )
        return msg
    if _has(blockers, "Sin breakout"):
        msg = (
            f"**Buena empresa pero el precio está esperando.** "
            f"La fuerza está ahí ({_strength_phrase(rs)}), los fundamentales también razonables, "
            "pero ahora mismo no hay disparador: el precio está consolidando, sin romper hacia arriba. "
        )
        if sector_p: msg += sector_p + " "
        msg += (
            "**Estrategia**: vigilarla cada día. El día que rompa con fuerza compradora real, "
            "ese es el momento de entrar."
        )
        return msg
    if _has(blockers, "Breakout sin confirmación"):
        return (
            f"**El precio sube hoy pero con poca convicción.** "
            f"Ha intentado romper hacia arriba pero la gente no se ha animado a comprar de verdad — "
            f"el volumen es bajo. Sin convicción de los compradores, los esos intentos de subida suelen fallar y "
            "el precio vuelve atrás. Esperar a que aparezca un día de subida con volumen alto antes de entrar."
        )
    if _has(blockers, "Fuerza relativa insuficiente"):
        return (
            f"**La empresa todavía no destaca frente al mercado.** "
            f"De momento {_strength_phrase(rs)}, así que no hay razón para preferirla a otras "
            "más fuertes. Si te gusta la tesis a largo plazo, espérala — cuando empiece a liderar, "
            "se notará en los rankings y tendrás margen para entrar."
        )
    if _has(blockers, "Medias") or _has(blockers, "SMA") or _has(blockers, "Lejos del máximo"):
        return (
            "**La tendencia de fondo todavía no es claramente alcista.** "
            "Aunque la empresa pueda gustar, los gráficos dicen que aún no está en posición de "
            "subir con continuidad. Esperar a que se construya una base sólida antes de entrar."
        )
    return "En seguimiento. Hoy no hay un disparador claro, pero la empresa merece estar en la lista."


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
