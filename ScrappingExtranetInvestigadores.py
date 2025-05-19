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
BATCH_SIZE  = 20
START_INDEX = 0
URL_BASE    = "https://extranet.ufro.cl/investigacion/ver_cv_investigacion.php"

# --- UTILIDADES ---
def split_name(fullname: str):
    """
    Divide 'Nombre Completo' en (nombre, paterno, materno):
      - 1 palabra  → (nombre, "", "")
      - 2 palabras → (parts[0], parts[1], "")
      - 3 palabras → (parts[0], parts[1], parts[2])
      - >=4 →       (parts[0], parts[-2], parts[-1])
    """
    parts = fullname.strip().split()
    n = len(parts)
    if n == 0:
        return "", "", ""
    if n == 1:
        return parts[0], "", ""
    if n == 2:
        return parts[0], parts[1], ""
    if n == 3:
        return parts[0], parts[1], parts[2]
    return parts[0], parts[-2], parts[-1]

def parse_table(section_title):
    """Extrae filas de la tabla inmediatamente posterior a un <h3> dado."""
    try:
        tbl = driver.find_element(
            By.XPATH,
            f"//h3[text()='{section_title}']/following-sibling::table[1]"
        )
        rows = tbl.find_elements(By.TAG_NAME, "tr")[1:]
        return " || ".join(
            " | ".join(td.text.strip() for td in row.find_elements(By.TAG_NAME, "td"))
            for row in rows
        )
    except:
        return ""

# Crear CSV con cabecera si no existe
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID","Nombre Buscado","Nombre Completo","Sexo","Unidad",
            "E-Mail","Título Profesional","Institución",
            "Proyectos","Publicaciones","Link CV PDF","Estado"
        ])

# Inicializar WebDriver
options = webdriver.ChromeOptions()
# options.add_argument("--headless")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)
wait = WebDriverWait(driver, 15)

# Leer Excel de entrada
df_in = pd.read_excel("UFRO_Planta2022-2024.xlsx", engine="openpyxl")
nombres = df_in["Nombre Completo"].tolist()

batch = []
_current_id = START_INDEX

for idx, nombre_full in enumerate(nombres[START_INDEX:], start=START_INDEX+1):
    _current_id += 1
    nombre, paterno, materno = split_name(nombre_full)

    # 1) Navegar al formulario
    driver.get(URL_BASE)
    wait.until(EC.presence_of_element_located((By.ID, "nombre_filtro")))

    # 2) Rellenar filtros y buscar
    driver.find_element(By.ID, "nombre_filtro").clear()
    driver.find_element(By.ID, "nombre_filtro").send_keys(nombre)
    driver.find_element(By.ID, "paterno_filtro").clear()
    driver.find_element(By.ID, "paterno_filtro").send_keys(paterno)
    driver.find_element(By.ID, "materno_filtro").clear()
    driver.find_element(By.ID, "materno_filtro").send_keys(materno)
    driver.find_element(By.XPATH, "//input[@value='BUSCAR']").click()

    # 3) Esperar la tabla de resultados
    try:
        wait.until(EC.presence_of_element_located((
            By.XPATH, "//table[contains(@class,'Tabla_lst')]/tbody/tr[position()>1]"
        )))
    except:
        batch.append({
            "ID": _current_id,
            "Nombre Buscado": nombre_full,
            "Estado": "Sin resultados"
        })
        print(f"[{_current_id}] {nombre_full}: Sin resultados")
        continue

    # 4) Buscar el enlace exacto y extraer su href (que es del tipo "javascript:Load(...)")
    rows = driver.find_elements(
        By.XPATH,
        "//table[contains(@class,'Tabla_lst')]/tbody/tr[position()>1]"
    )
    load_call = None

    for r in rows:
        cols = r.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 2:
          nombre_en_tabla = cols[1].text.strip().lower()
          if nombre_en_tabla == nombre_full.lower():
            a_tag = cols[1].find_element(By.TAG_NAME, "a")
            href = a_tag.get_attribute("href") or ""
            if href.startswith("javascript:Load"):
              load_call = href[len("javascript:"):]  # elimina "javascript:" para ejecutar
            break


    if not load_call:
        estado = "No se encontró enlace exacto"
        batch.append({"ID": _current_id, "Nombre Buscado": nombre_full, "Estado": estado})
        print(f"[{_current_id}] {nombre_full}: {estado}")
        continue

    # 5) Ejecutar la llamada Load(...) vía JS para cargar el perfil
    driver.execute_script(load_call)

    # 6) Esperar que cargue el div_cont y el campo "Investigador"
    try:
        wait.until(EC.presence_of_element_located((By.ID, "div_cont")))
        wait.until(EC.presence_of_element_located((
            By.XPATH, "//td[contains(text(),'Investigador')]/following-sibling::td"
        )))
    except:
        batch.append({
            "ID": _current_id,
            "Nombre Buscado": nombre_full,
            "Estado": "Perfil no cargó tras Load()"
        })
        print(f"[{_current_id}] {nombre_full}: Perfil no cargó tras Load()")
        continue

    # 7) Extraer datos del perfil
    def get_td(label):
        try:
            return driver.find_element(
                By.XPATH,
                f"//td[contains(text(),'{label}')]/following-sibling::td"
            ).text.strip()
        except:
            return ""

    info = {
        "ID": _current_id,
        "Nombre Buscado": nombre_full,
        "Nombre Completo": get_td("Investigador"),
        "Sexo": get_td("Sexo"),
        "Unidad": get_td("Unidad"),
        "E-Mail": get_td("E-Mail"),
        "Título Profesional": get_td("Título Profesional"),
        "Institución": get_td("Institución"),
        "Proyectos": parse_table("Proyectos"),
        "Publicaciones": parse_table("Publicaciones"),
        "Link CV PDF": "",
        "Estado": "OK"
    }

    # 8) Si existe un enlace a PDF, guardarlo
    try:
        info["Link CV PDF"] = driver.find_element(
            By.XPATH, "//a[contains(@href,'.pdf')]"
        ).get_attribute("href")
    except:
        pass

    batch.append(info)
    print(f"[{_current_id}] Procesado: {info['Nombre Completo']}")

    # 9) Volcar cada BATCH_SIZE registros al CSV
    if len(batch) >= BATCH_SIZE:
        pd.DataFrame(batch).to_csv(
            CSV_FILE, mode="a", index=False, header=False, encoding="utf-8-sig"
        )
        batch.clear()

# Volcar remanentes
if batch:
    pd.DataFrame(batch).to_csv(
        CSV_FILE, mode="a", index=False, header=False, encoding="utf-8-sig"
    )

driver.quit()
print("✅ Scraping completado. Resultados en", CSV_FILE)
