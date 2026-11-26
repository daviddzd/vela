# Modelo de negocio {#cap-negocio}

## En una frase

!!! frase "En una frase"
    **Enlaza cobra a cada institución una suscripción mensual según su tamaño; con los supuestos base deja de perder dinero
    en el mes {{ bm.breakeven_month }} y cada cliente paga con creces lo que cuesta conseguirlo, pero el valor presente del
    plan a cinco años es negativo al {{ bm.rate_25 }} y el mercado privado real (DENUE) es más chico de lo que el plan
    supone; el escenario recomendado lo resuelve con un tope de participación y un plan para centros públicos.**

## Explicado sin tecnicismos

Piensa en un gimnasio: cada socio paga una mensualidad. Al principio hay pocos socios y hay que pagar renta y sueldos
completos: se pierde dinero. Cada socio nuevo cuesta algo de publicidad. Si los socios se quedan muchos meses, cada uno
deja más de lo que costó atraerlo. El negocio funciona cuando hay suficientes socios para cubrir los costos fijos, y vale
la pena si lo que se gana después compensa lo que se perdió al principio (contando que el dinero de dentro de cinco años
vale menos que el de hoy).

Enlaza es ese gimnasio, pero sus socios son instituciones de cuidado y la mensualidad depende de cuántos pacientes
atienden.

## Por qué lo hicimos así

| Decidimos | En lugar de | Por qué |
|---|---|---|
| **Suscripción mensual por institución** ([[SaaS]]) | Comisión por servicio (alternativa evaluada: {{ neg.commission_alternative }} %) | Ingreso predecible para Enlaza y costo predecible para la institución; una comisión choca con instituciones de asistencia privada. |
| **Tres planes** por tamaño | Un solo precio | Una residencia de 40 pacientes y una red de 300 no pueden pagar lo mismo. |
| **Cada número con fuente o «supuesto»** | Cifras redondas «razonables» | Regla 11 del proyecto. `data/business/assumptions.csv` tiene {{ neg.assumptions_rows }} filas: {{ neg.assumptions_real }} con fuente real y enlace, el resto marcadas como supuesto. |
| **Un solo cálculo** para la página y el cuaderno | Una hoja de Excel aparte | `business_model.py` es el mismo código en `/negocio`, en `business/model.ipynb` y en este libro: no hay dos versiones de los números. |
| **Mercado del DENUE por segmento** | El total del sector | El total incluye establecimientos que no serían clientes. Contamos residencias, centros de día y enfermería a domicilio, privados y públicos. |
| **Tres escenarios** (base, conservador, recomendado) | Uno optimista | El base no cabe en el mercado; lo decimos y proponemos una alternativa. |

## Cómo funciona por dentro

### 1. Los planes y el ingreso promedio

| Plan | Pacientes | Precio mensual (supuesto) | Mezcla de clientes (supuesto) |
|---|---|---|---|
| Básico | hasta {{ seed.plan_limit_basic }} | {{ neg.plan_basic_price }} | {{ neg.plan_mix_basic }} % |
| Profesional | hasta {{ seed.plan_limit_professional }} | {{ neg.plan_professional_price }} | {{ neg.plan_mix_professional }} % |
| Institucional | {{ seed.plan_limit_institutional }} | {{ neg.plan_institutional_price }} | {{ neg.plan_mix_institutional }} % |

**Ingreso promedio por institución** (año 1) = suma de precio × mezcla = {{ bm.arpa1 }} al mes. Los precios suben con la
inflación ({{ neg.inflation_annual_oct_2026 }} %, INEGI) salvo en el caso pesimista.

Referencia de competencia (precios públicos, sin IVA): HuliPractice por médico de {{ neg.competitor_hulipractice_min }} a
{{ neg.competitor_hulipractice_max }} al mes; Doctoralia de {{ neg.competitor_doctoralia_starter }} a
{{ neg.competitor_doctoralia_vip }} por especialista. Enlaza cobra por **institución** e incluye la coordinación del personal.

### 2. Costos

- **Fijos:** {{ neg.founders }} fundadores × {{ neg.salary_software_developer_cdmx }} (salario de referencia de desarrollador en la
  CDMX, Indeed) × {{ neg.employer_cost_factor }} (carga patronal, supuesto) + {{ neg.infra_monthly_year1 }} de infraestructura =
  {{ bm.fixed1 }} al mes en el año 1.
- **Que crecen con los clientes** (supuestos editables): soporte (1 persona por cada {{ neg.institutions_per_support }}
  instituciones), hospedaje en la nube desde el año {{ neg.hosting_start_year }} (servidor + base de datos administrada, al tipo de
  cambio FIX de Banxico) y **adquisición**: {{ neg.cac_per_institution }} por institución nueva.

### 3. Punto de equilibrio

La fórmula clásica: costo fijo ÷ ingreso promedio = {{ bm.fixed1 }} ÷ {{ bm.arpa1 }} ≈ **{{ bm.breakeven_static }}**.

El modelo mes a mes (5 años, clientes {{ bm.y1.customers }} → {{ bm.y2.customers }} → {{ bm.y3.customers }} → {{ bm.y4.customers }} →
{{ bm.y5.customers }}, con cancelación de {{ neg.monthly_churn }} % al mes):

| Año | Instituciones al cierre | Utilidad del año |
|---|---|---|
| 1 | {{ bm.y1.customers }} | {{ bm.y1.profit }} |
| 2 | {{ bm.y2.customers }} | {{ bm.y2.profit }} |
| 3 | {{ bm.y3.customers }} | {{ bm.y3.profit }} |
| 4 | {{ bm.y4.customers }} | {{ bm.y4.profit }} |
| 5 | {{ bm.y5.customers }} | {{ bm.y5.profit }} |

- **Deja de perder dinero** en el mes {{ bm.breakeven_month }} (año {{ bm.breakeven_year }}).
- **Recupera lo perdido** (caja acumulada ≥ 0) en el mes {{ bm.payback_month }}.
- **Inversión necesaria** (el punto más bajo de la caja acumulada): {{ bm.investment }}, en el mes {{ bm.investment_month }}.

### 4. Valor presente neto (VPN)

El [[VPN]] trae a pesos de hoy los flujos de los cinco años, descontando con una tasa que refleja el riesgo. Tasa base
{{ bm.rate_25 }} (supuesto: tasa libre de riesgo, TIIE 28 días {{ neg.tiie_28_days }} %, más una prima de riesgo de empresa
nueva), con sensibilidad a {{ bm.rate_15 }} y {{ bm.rate_35 }}:

| Tasa | {{ bm.rate_15 }} | {{ bm.rate_25 }} | {{ bm.rate_35 }} |
|---|---|---|---|
| VPN a 5 años | {{ bm.npv_15 }} | **{{ bm.npv_25 }}** | {{ bm.npv_35 }} |

**Por qué es negativo a la tasa base:** los primeros años acumulan pérdidas (pocos clientes, costo fijo completo) y esas
pérdidas tempranas pesan más que las utilidades de los años 4 y 5, que se descuentan más. ¿Qué haría falta para que el
VPN base sea cero? Cada palanca por separado: precio Profesional de {{ bm.zero_price }}, o {{ bm.zero_year5 }} instituciones
en el año 5, o un costo de adquisición de {{ bm.zero_cac }}.

### 5. La unidad económica: LTV / CAC

| Concepto | Valor | Cómo se calcula |
|---|---|---|
| Margen mensual por institución | {{ bm.margin }} | ingreso promedio − soporte y hospedaje por institución ({{ bm.variable_cost }}) |
| Vida esperada de un cliente | {{ bm.lifetime }} | 1 ÷ cancelación mensual |
| [[LTV]] (valor de vida del cliente) | {{ bm.ltv }} | margen × vida (sin descontar) |
| [[CAC]] (costo de conseguirlo) | {{ bm.cac }} | supuesto |
| **LTV / CAC** | **{{ bm.ltv_cac }}** | una regla común es que sea mayor que 3 : 1 |
| Meses para recuperar el CAC | {{ bm.cac_payback }} | CAC ÷ margen mensual |

Conclusión: **cada cliente es rentable**; el problema del VPN no es la unidad, es el **costo fijo de los primeros años**
con pocos clientes.

### 6. El mercado real (DENUE, mayo de 2026)

Conteo por clase de actividad del directorio oficial del INEGI ([[DENUE]]), CDMX y Estado de México:

| Segmento | CDMX privados | CDMX públicos | Edomex privados | Edomex públicos |
|---|---|---|---|---|
| Residencias | {{ neg.denue_residences_private_cdmx }} | {{ neg.denue_residences_public_cdmx }} | {{ neg.denue_residences_private_edomex }} | {{ neg.denue_residences_public_edomex }} |
| Centros de día | {{ neg.denue_day_centers_private_cdmx }} | {{ neg.denue_day_centers_public_cdmx }} | {{ neg.denue_day_centers_private_edomex }} | {{ neg.denue_day_centers_public_edomex }} |
| Enfermería a domicilio | {{ neg.denue_home_nursing_cdmx }} | — | {{ neg.denue_home_nursing_edomex }} | — |

El mercado objetivo son los **privados** (supuesto: los públicos compran por licitación). Con el plan base, en el año 5
Enlaza tendría el {{ bm.sc.base.share_cdmx }} de los privados de la CDMX y el {{ bm.sc.base.share_edomex }} de los del Estado de
México: **demasiado** para una empresa nueva. El plan de {{ bm.y5.customers }} clientes no cabe en ese mercado.

### 7. Tres escenarios

| Escenario | Inversión necesaria | Mes de equilibrio | Recupera lo perdido | VPN al {{ bm.rate_25 }} | Instituciones año 5 |
|---|---|---|---|---|---|
| Base | {{ bm.sc.base.investment }} | {{ bm.sc.base.breakeven }} | {{ bm.sc.base.payback }} | {{ bm.sc.base.npv25 }} | {{ bm.sc.base.customers5 }} |
| Conservador (la mitad de clientes) | {{ bm.sc.conservative.investment }} | {{ bm.sc.conservative.breakeven }} | {{ bm.sc.conservative.payback }} | {{ bm.sc.conservative.npv25 }} | {{ bm.sc.conservative.customers5 }} |
| **Recomendado** | **{{ bm.sc.recommended.investment }}** | **{{ bm.sc.recommended.breakeven }}** | **{{ bm.sc.recommended.payback }}** | **{{ bm.sc.recommended.npv25 }}** | {{ bm.sc.recommended.customers5 }} |

**El recomendado** (decisión del equipo, 22 nov 2026): como máximo el {{ neg.recommended_private_cap }} % de los privados de cada entidad, expansión a
Jalisco y Nuevo León, un **plan Gobierno** para centros de día públicos ({{ bm.sc.recommended.gov5 }} centros en el año 5, a {{ neg.plan_government_price }} al mes; precio
supuesto, no hay referencia pública) y fundadores al {{ neg.founder_salary_year1_recommended }} % del sueldo el primer año. **Depende de esos dos supuestos
nuevos**: sin el plan Gobierno su VPN sería {{ bm.rec_wo_gov }}; sin el recorte a fundadores, {{ bm.rec_wo_cut }}; sin
ninguno de los dos, {{ bm.rec_wo_both }}.

![La página `/negocio`: tarjetas con ingreso, costo fijo, punto de equilibrio y meses clave; cada cifra dice su fuente o «supuesto», y los supuestos principales se pueden cambiar en vivo.](capturas/direccion_negocio.png){.media}

### 8. Lo que mide el prototipo

`/negocio` también muestra datos del uso real del prototipo: servicios coordinados por institución, asignaciones
automáticas, por coordinación y «por tiempo», y horas de coordinación ahorradas con el supuesto de
{{ neg.minutes_per_manual_assignment }} minutos por asignación manual evitada.

## Dónde está en el código

| Qué | Dónde |
|---|---|
| Todos los supuestos, con fuente y enlace | `data/business/assumptions.csv` |
| El cálculo (un solo módulo) | `backend/app/services/business_model.py` |
| Cuaderno para la materia | `business/model.ipynb` |
| Ruta y pantalla | `backend/app/routers/business.py`, `frontend/src/pages/BusinessPage.tsx` |
| Pruebas | `backend/tests/test_business.py` |
| Decisiones | `docs/spec/08_negocio.md`, `docs/dev/decisiones_paso_8.md` |

## Números clave

{{ tabla bm.arpa1 bm.fixed1 bm.breakeven_static bm.breakeven_month bm.payback_month bm.investment bm.npv_25 bm.ltv_cac bm.cac_payback neg.monthly_churn neg.cac_per_institution bm.sc.recommended.npv25 neg.market_care_residences_cdmx }}

## Limitaciones honestas

- **Los precios, la mezcla de planes, la cancelación, el CAC y el crecimiento son supuestos**: no hay clientes reales ni
  entrevistas de disposición a pagar.
- **El plan Gobierno no tiene un precio de referencia público**; es el supuesto más débil del escenario recomendado.
- **No se modeló un CAC más alto** para vender en otros estados.
- **Pesos nominales, antes de impuestos, sin IVA y sin inversión inicial** (supuestos).
- **El mercado del DENUE no tiene una clase para clínicas geriátricas**: no se cuentan.
- **El VPN base es negativo.** No lo escondemos: es lo que justifica el escenario recomendado.

## Preguntas que te pueden hacer

!!! pregunta "¿Cómo gana dinero Enlaza?"
    Con una suscripción mensual por institución: Básico, Profesional o Institucional según el número de pacientes. El
    ingreso promedio, con la mezcla de planes supuesta, es {{ bm.arpa1 }} al mes por institución.

!!! pregunta "¿Cuál es el punto de equilibrio?"
    Con la fórmula clásica, {{ bm.breakeven_static }}: {{ bm.fixed1 }} de costo fijo ÷ {{ bm.arpa1 }} de ingreso promedio. Con el
    modelo mes a mes, Enlaza deja de perder dinero en el mes {{ bm.breakeven_month }} y recupera lo perdido en el mes
    {{ bm.payback_month }}.

!!! pregunta "Si el VPN es negativo, ¿el negocio no sirve?"
    Con la tasa base de {{ bm.rate_25 }} y el plan base, el VPN es {{ bm.npv_25 }}: las pérdidas de los primeros años pesan más
    que las utilidades de los últimos. Pero la unidad es muy rentable (LTV/CAC {{ bm.ltv_cac }}). Por eso propusimos el escenario
    recomendado, con VPN {{ bm.sc.recommended.npv25 }}, y decimos de qué supuestos depende.

!!! pregunta "¿Qué es LTV/CAC y por qué importa?"
    LTV es cuánto deja un cliente en toda su vida (margen mensual × meses que se queda); CAC es cuánto cuesta conseguirlo.
    Si LTV/CAC es mayor que 3, cada cliente paga con creces su adquisición. El nuestro es {{ bm.ltv_cac }} y el CAC se recupera
    en {{ bm.cac_payback }}.

!!! pregunta "¿De dónde sacaron el tamaño del mercado?"
    Del DENUE del INEGI (mayo de 2026), contando por clase de actividad: residencias, centros de día y enfermería a
    domicilio, privados y públicos, en la CDMX y el Estado de México. Por ejemplo, {{ neg.denue_residences_private_cdmx }}
    residencias privadas en la CDMX. Coincide con DataMéxico.

!!! pregunta "¿Por qué no cobrar una comisión por servicio?"
    La evaluamos ({{ neg.commission_alternative }} % por servicio) y la descartamos como principal: el ingreso sería variable y
    choca con instituciones de asistencia privada, que no deberían pagar más por atender más.

!!! pregunta "¿Los números de la página son los mismos del cuaderno?"
    Sí: la página, el cuaderno y este libro usan el mismo `business_model.py` sobre el mismo `assumptions.csv`. Si cambia un
    supuesto, cambian los tres.
