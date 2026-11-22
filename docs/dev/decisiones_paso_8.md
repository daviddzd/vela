# Paso 8 · Negocio, privacidad y consentimientos: decisiones y resultados

Rama `feature/negocio-privacidad`. Capturas en el proyector: `docs/dev/capturas/negocio/` y
`docs/dev/capturas/privacidad/`.

## 1. `/negocio` (dirección)
- **Un solo cálculo:** `backend/app/services/business_model.py` lee `data/business/assumptions.csv`. La
  página y el cuaderno `business/model.ipynb` usan el mismo módulo. Cada fila del CSV dice si es dato `real`
  (con fuente y enlace) o `assumption` (supuesto); la página muestra el enlace o la etiqueta «supuesto».
- **Modelo mensual, 5 años, pesos nominales** (decisión del equipo, 22 nov 2026):
  - Clientes: cada mes se pierde el churn y entran altas constantes dentro de cada año, calculadas para
    cerrar el año en la meta (5, 15, 30, 50, 75).
  - Ingresos: clientes × ingreso promedio (mezcla de planes × precios). Los precios suben con la inflación
    (3.75 %, INEGI) salvo que se apague el ajuste (caso pesimista).
  - Costos fijos: 4 fundadores × 17,678 (Indeed) × 1.35 + 3,000, ajustados por inflación.
  - Costos que crecen con los clientes (todos editables y marcados como supuesto):
    - **Soporte:** 1 persona por cada 25 instituciones, a partir de 25. Salario de referencia 8,900 MXN
      (DataMéxico, auxiliares y técnicos en informática, 2026-T1) × carga patronal.
    - **Hospedaje en producción desde el año 2:** DigitalOcean Basic Droplet 4 vCPU / 8 GiB (48 USD) +
      PostgreSQL administrado 2 vCPU / 4 GiB (60.90 USD), por cada 25 instituciones, al FIX de Banxico del
      20 nov 2026 (19.0228 MXN/USD; el tipo de cambio fijo es supuesto). La laptop solo sirve para el prototipo.
    - **Adquisición:** 15,000 MXN por institución nueva (supuesto).
  - Tasas de descuento nominales: 15, 25 y 35 %. Antes de impuestos, sin IVA, sin inversión inicial (supuesto).
- **Competencia** (precios públicos, sin IVA): HuliPractice por médico 490–2,540 y para clínicas desde
  1,250/1,400 con 3 profesionales (vía comparativa de Medesk); Doctoralia PRO 1,740–2,970 por especialista;
  Nimbo no publica precio; GERIGES (España) 49–119 EUR. Todas las fuentes están en el CSV.
- **Uso real del prototipo:** servicios coordinados por institución y aprobaciones automáticas, por
  coordinación y «por tiempo»; horas ahorradas con el supuesto de 3 min por asignación; ingreso recurrente
  con el plan contratado de cada institución activa (la tabla `invoices` de la semilla está vacía).

### Resultado (caso base)
| | Valor |
|---|---|
| Ingreso promedio por institución | 5,500 MXN/mes |
| Costo fijo mensual año 1 | 98,461 MXN |
| Punto de equilibrio de la especificación (costo fijo ÷ ingreso promedio) | 18 instituciones |
| Mes desde el que ya no se pierde dinero | **mes 30 (año 3)** |
| Mes en que se recupera lo perdido (caja acumulada ≥ 0) | mes 53 (año 5) |
| VPN 15 % / 25 % / 35 % | +300,323 / **−163,128** / −444,411 MXN |
| Caso pesimista (precios congelados) | mes 34 (año 3); recuperación mes 58; VPN al 25 % −632,038 |

**El punto de equilibrio sigue en el año 3**, aun con soporte, hospedaje y adquisición. Lo que cambia es el
valor del negocio: con la tasa base de 25 % el VPN es **negativo**. Por qué: los años 1 a 3 acumulan
1.8 millones de pérdidas (empiezan con 0 clientes y el costo fijo completo), y esas pérdidas tempranas pesan
más que las utilidades de los años 4 y 5, que se descuentan más. El costo de adquisición es lo que más pesa:
sin él, el VPN al 25 % sería +648,018 y la recuperación llegaría en el mes 47; con el plan Profesional a
7,000 sería +223,514 (cálculos con el mismo modelo, para la discusión; no son metas).

### Inversión, unidad económica y qué haría falta (decisión del equipo, 22 nov 2026)
| Tarjeta | Caso base | Cómo se calcula |
|---|---|---|
| Inversión necesaria | **1,896,844 MXN**, en el mes 29 (año 3) | el punto más bajo de la caja acumulada |
| LTV / CAC | **21.9 : 1** | margen 4,937 al mes × 67 meses de vida (1 ÷ churn 1.5 %) ÷ CAC 15,000 |
| Meses para recuperar el CAC | **3.0** | CAC ÷ margen mensual (ingreso promedio − soporte y hospedaje por institución: 563) |

LTV/CAC y la recuperación del CAC no descuentan ni incluyen costos fijos: dicen que cada cliente paga con
creces lo que cuesta conseguirlo; el problema del VPN es el costo fijo de los primeros años con pocos clientes.

**¿Qué haría falta para que el VPN al 25 % sea positivo?** (cada palanca por separado; análisis, no meta):
plan Profesional a **6,422** (hoy 6,000), **100** instituciones en el año 5 (hoy 75) o un CAC de **11,983**
(hoy 15,000). Se calcula por bisección sobre el mismo modelo (`what_for_npv_zero`).

### Mercado realista (DENUE, INEGI, mayo de 2026)
Fuente: descarga masiva del DENUE, sector 62 (`denue_00_62_csv.zip`), conteo por clase SCIAN y entidad. Coincide
con DataMéxico en los 109 asilos de la CDMX (88 privados + 21 públicos).

| Segmento | CDMX privados | CDMX públicos | Edomex privados | Edomex públicos |
|---|---|---|---|---|
| Residencias (623311 / 623312) | 88 | 21 | 48 | 45 |
| Centros de día (624121 / 624122) | 22 | 104 | 20 | 218 |
| Enfermería a domicilio (621610, sin separación) | 7 | — | 33 | — |
| Clínicas geriátricas | sin clase propia en DENUE (no se cuentan) | | | |

Mercado objetivo = privados (supuesto: los públicos compran por licitación). Expansión (supuesto): CDMX primero;
desde el año 3, la mitad de las altas son del Estado de México. En el año 5: **CDMX 42 de 117 = 35.8 %**,
**Edomex 33 de 101 = 32.8 %**. Supera el 10 %, así que se muestra el **escenario conservador** (la mitad de
los clientes: 3, 8, 15, 25, 38): ya no se pierde dinero desde el mes 44 (año 4), **no recupera lo perdido en
5 años**, necesita 2.86 millones (mes 43) y el VPN al 25 % es −1.92 millones. Aun así tendría 17.9 % de la
CDMX. Conclusión para la defensa: el plan de 75 clientes no cabe en el mercado privado de CDMX y Edomex con
estos segmentos; habría que ampliar el mercado (más entidades, instituciones públicas, redes de cuidado
informales) o subir el ingreso por cliente.

**Enteros:** la tabla por año muestra instituciones redondeadas, con una nota: el cálculo usa valores esperados
(con decimales) por el churn mensual.

## Pruebas en otra base de datos
`pytest` ya no usa la base de la demo: `tests/conftest.py` cambia la base de la conexión a `vela_test` antes de
cargar la app y se detiene si no está conectado a ella. `scripts/create_test_db.py` crea `vela_test` con el
mismo SQL, la misma semilla, los mismos permisos de `vela_api` y las mismas migraciones (4 s). Comprobado: la
bitácora de la demo tenía 11,628 filas antes y después de correr las 132 pruebas. La guía («Día de la
defensa», paso 3) explica cómo recrear la base de la demo desde cero para que la bitácora solo muestre los
ensayos (no se ejecutó aquí: borra la base de la demo).

## 2. `/privacidad`
- **Aviso de privacidad** en pantalla para todos los roles, leído de `docs/legal/aviso_de_privacidad.md`.
  Se actualizó: los derechos se ejercen en «Privacidad» (antes decía «Mi cuenta», que no existe) y se citan
  los plazos.
- **Plazo ARCO verificado** en el texto vigente de la LFPDPPP (DOF 20-03-2025, última reforma 14-11-2025,
  Cámara de Diputados): **art. 31**, respuesta en un máximo de **20 días** desde que se recibe la solicitud y,
  si procede, se hace efectiva dentro de los **15 días** siguientes; ambos plazos se pueden ampliar una vez
  por un periodo igual. **Art. 2, fr. VIII:** «Días: Días hábiles». Art. 28: contenido de la solicitud.
  Art. 34: es gratuito. El 20 está en `assumptions.csv` con su fuente; el código no lo tiene escrito.
- **Formulario ARCO:** crea una solicitud con folio (`ARCO-00001`…) en `arco_requests` (con RLS), queda en la
  bitácora y muestra la fecha límite. La fecha cuenta de lunes a viernes y **no descuenta días festivos**: la
  pantalla lo dice. Coordinación ve las de su institución; dirección, todas; los demás, las suyas.
- **Bitácora (dirección):** filtros por acción, usuario, fechas y permitido/bloqueado, 50 por página, y un
  resumen de los últimos 30 días: bloqueos por tipo, por día y los 5 usuarios con más bloqueos.
  **Ojo en la defensa:** casi todos los bloqueos de la bitácora los dejaron las pruebas automáticas (prueban
  a propósito intentos indebidos y esos registros se quedan, porque la bitácora no se borra). La pantalla lo
  avisa.

## 3. Consentimientos (coordinación)
- Registrar o renovar: tipo, quién firma (la persona o un familiar registrado como **representante legal de
  esa misma persona**), asentimiento, fecha de firma y vencimiento. Revocar pide un motivo. Migración `0008`.
- **La revocación surte efecto al momento:** el consentimiento queda con `granted = false`, y cada función
  revisa `v_consents.is_valid` en cada petición. Además se envía el evento `consent.changed`.
  - `home_care`: se cancelan las visitas pendientes (motivo «consentimiento revocado») y se alerta a
    coordinación. Una visita **en curso no se cancela sola**: la alerta pide que coordinación decida. La
    familia recibe un aviso. Las solicitudes nuevas se rechazan.
  - `health_data`: los datos de salud dejan de mostrarse. `voice_assistant`: el asistente deja de aceptar notas.
- Nadie fuera de coordinación puede registrar ni revocar, y no se pueden tocar consentimientos de otra
  institución (403 y queda en la bitácora).
- Pruebas: `backend/tests/test_consents.py` (8) y `backend/tests/test_business.py` (6).
- `scripts/reset_demo.py` ahora también borra las solicitudes ARCO y regresa los consentimientos a los valores
  de la semilla (después de un ensayo en el que se revocó alguno).
