# Sistema inteligente de rutas — Generador de dataset y motor de rutas
Repositorio con un script autocontenido que genera un dataset sintético de rutas de transporte (CSV), construye una base de conocimiento en forma de grafo, aplica reglas simples (bloqueos, preferencia accesible, penalización por transbordo) y calcula la mejor ruta entre dos paradas usando una variante de Dijkstra que considera cambios de línea.
---
## Requisitos
* **Python** 3.8+
* Paquetes Python:
  * **pandas**
  * **networkx**
Instalación rápida (virtualenv recomendado):
```bash
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install pandas networkx
```
---
Estructura del repositorio
* `transporte_ruta_con_dataset.py` — Script principal (genera CSV, construye grafo, aplica reglas y calcula ruta).
* `bogota_transit_dataset_500.csv` — (generado) dataset sintético con 500 rutas.
* [`README.md`](https://README.md) — Documentación (este archivo).
---
## Uso rápido
### Clonar el repositorio y entrar en la carpeta
```bash
git clone https://github.com/iberoamericana-mantenimiento/inteligencia-artificial-actividad-2.git
cd https://github.com/iberoamericana-mantenimiento/inteligencia-artificial-actividad-2.git
```
### Ejecutar el script (regenerará el dataset y ejecutará la demo)
```bash
python transporte_ruta_con_dataset.py
```
### Resultado esperado (resumen)
* Mensaje de confirmación: `✅ Archivo creado: bogota_transit_dataset_500.csv`.
* Conteo de nodos y arcos del grafo.
* Ruta encontrada con coste estimado, número de transbordos y detalle tramo a tramo.
---
## Configuración y personalización
Dentro de `transporte_ruta_con_dataset.py` en la función `main()` puedes editar el diccionario **reglas**:
* **bloquear_estaciones**: lista de nombres de estaciones a remover del grafo.\
  Ejemplo:
  ```py
  reglas["bloquear_estaciones"] = ["La Candelaria"]
  ```
* **preferir_accesible**: booleano; si es True, penaliza aristas hacia estaciones no accesibles.
* **penalizacion_no_accesible**: minutos añadidos cuando la parada destino no es accesible.
* **penalizar_transbordo_min**: minutos extra al cambiar de línea (usado por Dijkstra adaptado).
Cambiar origen/destino de la demo:
```py
origen = "Usme"
destino = "Chía"
```
Ajustar número de rutas generadas:
```py
generate_dataset(csv_path, num_routes=500)
```
---
## Cómo funciona (resumen técnico)
* **Generador de dataset**: crea un CSV con rutas sintéticas. Cada fila contiene `stops_list`, `total_travel_time_min`, `route_id`, `mode`, `operator`, etc.
* **Construcción de la KB**: cada parada en `stops_list` se convierte en nodo; cada tramo consecutivo entre paradas en arista con atributo `tiempo` y `linea = route_id`. Si varias rutas comparten el mismo tramo, se conserva el de menor tiempo.
* **Atributos de estación**: para el ejemplo se generan atributos sintéticos reproducibles (lat/lon, estado, accesible). Si tienes coordenadas reales, sustituye la función `synth_station_attributes`.
* **Reglas**: se aplican sobre el grafo (eliminación de nodos, aumento de pesos por accesibilidad, etc.).
* **Búsqueda**: variante de Dijkstra donde el estado incluye la línea previa; al cambiar de línea se añade la penalización por transbordo.
---
## Comandos y pruebas sugeridas
* Ejecutar demo completa (regenera dataset):
```bash
python transporte_ruta.py
```
* Cambios rápidos (editar `reglas` en `main()`):
  * Sin bloqueos:
    ```py
    reglas["bloquear_estaciones"] = []
    ```
  * Penalización alta por transbordo:
    ```py
    reglas["penalizar_transbordo_min"] = 30
    ```
  * Mayor penalización por accesibilidad:
    ```py
    reglas["penalizacion_no_accesible"] = 100
    ```
Comparar salidas entre ejecuciones para ver el efecto de las reglas.
---
## Autores
* Diego Alejandro Beltran
* Ana Yesmit Contreras
* Jhonatan Rico
---
Gracias por usar este proyecto.