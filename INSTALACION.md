# Instalación y uso — Swing Screener

## Requisitos previos

Python ya está instalado (Python 3.12 vía Scoop en `~\scoop\apps\python`).

---

## Primer arranque (solo una vez)

```powershell
cd G:\workspace\external\swing-screener

# Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

> Si PowerShell rechaza el script de activación:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

---

## Lanzar la interfaz web

```powershell
cd G:\workspace\external\swing-screener
.\.venv\Scripts\streamlit.exe run app.py
```

Abre automáticamente en **http://localhost:8501**

Si el navegador no abre solo:
```powershell
start http://localhost:8501
```

---

## Flujo diario

1. Abre la interfaz web (comando arriba)
2. Pulsa **"🔄 Actualizar (rápido)"** en la barra lateral para descargar precios frescos y recalcular
3. Usa los filtros para ver Comprar / Vigilar / Vender / Saltar
4. Busca una empresa por nombre o ticker en el buscador

Alternativa rápida para probar solo 10 valores: botón **"🚀 Smoke (10)"**.

---

## Universo cubierto

~525 tickers: S&P 500 + Nasdaq-100 + extras configurados en `config.yaml`.

Extras incluidos por defecto: TSM, ASML, ARM, SE, SHOP, SPOT, NVO, BABA, BIDU, JD, PDD, TM, HOOD, RBLX, DKNG, DASH, SNDK.

Para añadir más tickers, edita la sección `universe.extra` en `config.yaml`:

```yaml
universe:
  extra:
    - TICKER1
    - TICKER2
```

---

## Configuración API (opcional)

La API key de Financial Modeling Prep ya está configurada en `config.yaml`.

En modo `yfinance_only` (por defecto para el universo completo) no hace falta. FMP se puede usar para el top-N de candidatos si el plan de API lo permite.

---

## Notebook (análisis manual)

```powershell
.\.venv\Scripts\jupyter.exe notebook notebooks\daily_screen.ipynb
```

O abre `notebooks/daily_screen.ipynb` en VS Code y selecciona el kernel `.venv`.

---

## Problemas comunes

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError` al lanzar | Activa el venv: `.\.venv\Scripts\Activate.ps1` |
| Yahoo devuelve 429 | Espera 10 min y pulsa Actualizar de nuevo |
| La app muestra "No hay datos" | Pulsa Smoke o Actualizar para generar el primer resultado |
| Gráfico no carga en una tarjeta | Error temporal de yfinance — ignora o recarga |
| PowerShell bloquea el venv | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
