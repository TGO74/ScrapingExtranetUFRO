# -----------------------------------------------------------------------------
# Scraper para extraer datos de investigadores de la Universidad de La Frontera
# -----------------------------------------------------------------------------
# LEER README.md para instrucciones de uso
# -----------------------------------------------------------------------------

import time
import csv
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN BÁSICA ---
CSV_FILE    = "resultados_investigadores.csv"
BATCH_SIZE  = 2
START_INDEX = 0
URL_BASE    = "https://extranet.ufro.cl/investigacion/ver_cv_investigacion.php"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "pdfs")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- UTILIDADES ---
def split_name(fullname: str):
    parts = fullname.strip().split()
    if len(parts) <= 3:
        return (parts + ["","",""])[:3]
    return parts[0], parts[-2], parts[-1]

def extract_personal():
    """Extrae las cuatro filas de Datos Personales."""
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#div_cont table")))
    tabla = driver.find_element(By.CSS_SELECTOR, "#div_cont table")
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:5]
    datos = {}
    for fila in filas:
        c = fila.find_elements(By.TAG_NAME, "td")
        key = c[1].text.strip().rstrip(":")
        val = " ".join(c[2].text.strip().split())
        datos[key] = val
    return datos

def extract_academic_degrees():
    """
    Construye un string con todos los grados académicos,
    separados por '||' para que queden juntos en una sola columna.
    """
    tablas = driver.find_elements(By.CSS_SELECTOR, "#div_cont table")
    degrees = []
    # Encuentra índice de la tabla "TITULOS/GRADOS ACADÉMICOS"
    for i, tbl in enumerate(tablas):
        th = tbl.find_elements(By.TAG_NAME, "th")
        if th and "TITULOS/GRADOS ACADÉMICOS" in th[0].text.upper():
            # Las 3 tablas siguientes contienen los grados
            for deg_tbl in tablas[i+1:i+4]:
                label = None
                val   = None
                # Primera fila de cada tabla: Titulo Profesional / Doctor / Magíster
                first_row = deg_tbl.find_elements(By.TAG_NAME, "tr")[0]
                cells = first_row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    label = cells[0].text.strip().rstrip(":")
                    # Combina texto y país (span)
                    txt = cells[1].text.strip().replace("\n", " ")
                    val = " ".join(txt.split())
                if label and val:
                    degrees.append(f"{val}")
            break
    # Une con '||' entre cada grado
    return " || ".join(degrees)

def extract_all_tables():
    """
    Convierte a texto todas las tablas excepto la primera
    (Datos Personales) y las académicas.
    """
    tablas = driver.find_elements(By.CSS_SELECTOR, "#div_cont table")
    # localizar índice académico
    acad_idx = None
    for i, tbl in enumerate(tablas):
        th = tbl.find_elements(By.TAG_NAME, "th")
        if th and "TITULOS/GRADOS ACADÉMICOS" in th[0].text.upper():
            acad_idx = i
            break

    resultados = []
    for idx, tbl in enumerate(tablas):
        if idx == 0 or (acad_idx is not None and acad_idx <= idx <= acad_idx+3):
            continue
        filas = tbl.find_elements(By.TAG_NAME, "tr")
        texto = " || ".join(
            " | ".join(td.text.strip() for td in fila.find_elements(By.TAG_NAME, "td"))
            for fila in filas[1:]
        )
        resultados.append(texto)
    return " ~~ ".join(resultados)

# --- Crear CSV con cabecera si no existe ---
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow([
            "Investigador","E-Mail","Fono/Anexo","Unidad(es)",
            "Grados Académicos","Tablas (todas)","PDF_Local","Estado"
        ])

# --- Inicializar WebDriver ---
options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "plugins.always_open_pdf_externally": True
})
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)
wait = WebDriverWait(driver, 15)

# --- Leer Excel de entrada ---
df = pd.read_excel("UFRO_Planta2022-2024.xlsx", engine="openpyxl")
nombres = df["Nombre Completo"].tolist()

batch = []
_current_id = START_INDEX

for nombre_full in nombres[START_INDEX:]:
    _current_id += 1
    nombre, paterno, materno = split_name(nombre_full)

    # 1) Abrir y buscar
    driver.get(URL_BASE)
    wait.until(EC.presence_of_element_located((By.ID, "nombre_filtro")))
    driver.find_element(By.ID, "nombre_filtro").send_keys(nombre)
    driver.find_element(By.ID, "paterno_filtro").send_keys(paterno)
    driver.find_element(By.ID, "materno_filtro").send_keys(materno)
    driver.find_element(By.XPATH, "//input[@value='BUSCAR']").click()

    # 2) Esperar resultados
    try:
        wait.until(EC.presence_of_element_located((
            By.XPATH, "//table[contains(@class,'Tabla_lst')]/tbody/tr[position()>1]"
        )))
    except:
        batch.append({
            "Investigador": nombre_full, "E-Mail": "", "Fono/Anexo": "",
            "Unidad(es)": "", "Grados Académicos": "",
            "Tablas (todas)": "", "PDF_Local": "", "Estado": "Sin resultados"
        })
        continue

    # 3) Cargar perfil
    load_js = None
    for row in driver.find_elements(By.XPATH,
            "//table[contains(@class,'Tabla_lst')]/tbody/tr[position()>1]"):
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 2 and cols[1].text.strip().lower() == nombre_full.lower():
            href = cols[1].find_element(By.TAG_NAME, "a").get_attribute("href") or ""
            if href.startswith("javascript:Load"):
                load_js = href.split("javascript:")[1]
            break

    if not load_js:
        batch.append({
            "Investigador": nombre_full, "E-Mail": "", "Fono/Anexo": "",
            "Unidad(es)": "", "Grados Académicos": "",
            "Tablas (todas)": "", "PDF_Local": "", "Estado": "Enlace no encontrado"
        })
        continue

    driver.execute_script(load_js)
    time.sleep(2)
    wait.until(EC.presence_of_element_located((By.ID, "div_cont")))

    # 4) Extraer datos
    personal = extract_personal()
    degrees  = extract_academic_degrees()
    tablas    = extract_all_tables()

    info = {
        "Investigador":      personal.get("Investigador",""),
        "E-Mail":            personal.get("E-Mail",""),
        "Fono/Anexo":        personal.get("Fono/Anexo",""),
        "Unidad(es)":        personal.get("Unidad(es)",""),
        "Grados Académicos": degrees,
        "Tablas (todas)":    tablas,
        "PDF_Local":         "",
        "Estado":            "OK"
    }

    batch.append(info)
    print(f"[{_current_id}] Procesado: {info['Investigador']}")

    # 5) Volcado parcial
    if len(batch) >= BATCH_SIZE:
        pd.DataFrame(batch).to_csv(
            CSV_FILE, mode="a", index=False, header=False, encoding="utf-8-sig"
        )
        batch.clear()

# 6) Volcar remanentes y cerrar
if batch:
    pd.DataFrame(batch).to_csv(
        CSV_FILE, mode="a", index=False, header=False, encoding="utf-8-sig"
    )

driver.quit()
print("✅ Scraping completado. Resultados en", CSV_FILE)

# -----------------------------------------------------------------------------
# Autor:       Tomás Eduardo Gutiérrez Olcay, Estudiante Ingeniería Civil Industrial mención Informática 
# Organización:Universidad de La Frontera – Equipo de Datos VRIP UFRO
# Email:       t.gutierrez04@ufromail.cl
# Fecha:       20/05/2025
# Proyecto:    Scraping de CVs investigadores UFRO
# Versión:     1.0
# Licencia:    MIT License
# -----------------------------------------------------------------------------

