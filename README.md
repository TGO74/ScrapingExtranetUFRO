# Scraping Extranet Investigadores UFRO

Este proyecto automatiza la extracción de información curricular de investigadores desde la plataforma Extranet de investigadores de la Universidad de La Frontera (UFRO). Utiliza Selenium para interactuar con la interfaz web, extrae datos personales y académicos, guarda los resultados en un CSV y descarga los CVs en PDF.

# *Falta modificar la el guardado de pdf y como se estan guardando los datos. Se esta trabajando en normalizarlos en tablas)
---

## 📁 Estructura del proyecto

```
├── pdfs/                           # Carpeta donde se guardan los PDF descargados
├── resultados_investigadores.csv   # Archivo de resultados acumulados
├── UFRO_Planta2022-2024.xlsx       # Excel de entrada con nombres de investigadores (cambiar por BD adecuada con listado actualizado de invetigadores UFRO)
├── ScraperExtranet.py                      # Script principal de scraping (el código provisto)
└── README.md                       # Documentación de uso
```

---

## 🛠️ Requisitos

* Python 3.8 o superior
* Google Chrome instalado
* Conexión a internet

**Dependencias de Python** (instalar con `pip install -r requirements.txt`):

```text
selenium
webdriver-manager
pandas
openpyxl
```

> *Opcional*: Si no cuentas con un `requirements.txt`, instala manualmente:
>
> ```bash
> pip install selenium webdriver-manager pandas openpyxl
> ```

---

## ⚙️ Configuración

* `CSV_FILE`: ruta y nombre del CSV que almacenará los resultados.
* `BATCH_SIZE`: número de registros que se procesan antes de volcar al CSV (por defecto 2).
* `START_INDEX`: índice desde el cual iniciar el conteo (útil para reanudar scraping).
* `URL_BASE`: URL base del formulario de búsqueda de CV.
* `DOWNLOAD_DIR`: carpeta donde se guardarán los PDF. Se crea automáticamente si no existe.
* `UFRO_Planta2022-2024.xlsx`: libro de Excel con columna `Nombre Completo` con los nombres completos de los investigadores.

Asegúrate de ubicar el archivo Excel en la misma carpeta que el script, o modifica la ruta en `pd.read_excel()`.

---

## 🚀 Uso

1. Clona o descarga este repositorio.
2. Instala las dependencias.
3. Coloca `UFRO_Planta2022-2024.xlsx` junto al script.
4. Ejecuta:

   ```bash
   python scraper.py
   ```
5. Al finalizar, encontrarás:

   * **resultados\_investigadores.csv** con los datos extraídos.
   * Carpeta **pdfs/** con los CVs en PDF.

---

## 🔍 Descripción del código

1. **Imports y configuración básica**:

   * Se importan módulos (`selenium`, `pandas`, `csv`, `time`, `os`).
   * Definición de constantes (rutas, URL, batch size, etc.).

2. **Funciones auxiliares**:

   * `split_name(fullname)`: separa el nombre completo en nombre, apellido paterno y materno.
   * `extract_personal()`: extrae datos personales (Investigador, E-Mail, Fono/Anexo, Unidad(es)).
   * `extract_academic_degrees()`: recorre las tablas para obtener todos los títulos y grados académicos.
   * `extract_all_tables()`: captura el contenido de todas las tablas restantes (publicaciones, proyectos, etc.).

3. **Inicialización de CSV**:

   * Si no existe, crea `resultados_investigadores.csv` con cabecera.

4. **Inicialización de Selenium**:

   * Configura `ChromeOptions` para descargas automáticas de PDF.
   * Inicia WebDriver con `ChromeDriverManager`.

5. **Lectura de Excel**:

   * Carga la lista de nombres desde la columna `Nombre Completo`.

6. **Bucle principal de scraping**:

   * Itera sobre los nombres (respetando `START_INDEX`).
   * Abre la URL de búsqueda, ingresa nombre, paterno y materno, y ejecuta la búsqueda.
   * Si no hay resultados, registra el estado "Sin resultados".
   * Si hay resultados, busca la fila coincidente y ejecuta el JavaScript `Load` para cargar el CV.
   * Espera la carga, extrae datos personales, grados académicos y tablas.
   * Agrega la información al batch y muestra en consola el progreso.
   * Cada `BATCH_SIZE` registros, vuelca los datos parciales al CSV.

7. **Volcado final y cierre**:

   * Vuelca cualquier registro restante.
   * Cierra el WebDriver.
   * Mensaje de finalización.

---

## 🛡️ Consideraciones y mejoras

* **Manejo de errores**: Actualmente el script continúa si no encuentra resultados o enlaces, pero podría mejorarse con más excepciones.
* **Descarga de PDF**: Se descarga automáticamente, pero no se registra la ruta en el CSV (campo `PDF_Local`).
* **Paralelización**: Para un gran volumen de investigadores, podría mejorarse con procesamiento concurrente.
* **Actualizar manejo de excepciones con nombres compuestos**: nombres compuestos o investigadores con mas de dos nombres estan causando problemas al encontrarlos.

---

*Desarrollado por Tomás Eduardo Gutiérrez Olcay - Fecha: 20/05/2025*

