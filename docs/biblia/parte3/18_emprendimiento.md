# Emprendimiento {#cap-m-emp}

<p class="responsable">Responsable: {{ equipo.materias.emprendimiento }}</p>

## En una frase

!!! frase "Lo que aporta esta materia"
    **Enlaza es un negocio SaaS para instituciones de cuidado: un problema real de coordinación, una propuesta de valor
    clara, tres planes de suscripción, un modelo financiero a cinco años con cada supuesto marcado, un mercado medido con
    el DENUE y la honestidad de decir que el plan base no alcanza y qué haría falta.**

## Qué evalúa el profesor

Normalmente: el **problema** y el **cliente**, la **propuesta de valor**, el **modelo de negocio** (cómo se gana dinero), el
**tamaño del mercado**, la **competencia**, las **proyecciones financieras** (equilibrio, flujo, VPN), las **métricas** de
negocio (LTV, CAC, churn) y la **viabilidad**. (Confirmen con el programa del profesor.)

## Los conceptos, desde cero

### Problema, cliente y usuario

**Qué es.** El **cliente** paga; el **usuario** usa. No siempre son la misma persona.

**En Enlaza.** Cliente: la **institución** (residencia, centro de día, red de cuidado a domicilio). Usuarios: coordinación,
personal, médicos y familias. El problema: coordinar visitas con llamadas, WhatsApp y hojas de cálculo (@ref(cap-que-es)).

### Propuesta de valor

**Qué es.** Por qué un cliente elegiría tu producto: qué dolor quita o qué ganancia da.

**En Enlaza.** «Cada visita, con la persona adecuada y a tiempo»: asignación automática que respeta turnos y ley, tablero en
vivo, familias informadas, alerta de emergencias por voz, indicadores y datos protegidos, sin instalar nada.

### Modelo de negocio y Lienzo (Canvas)

**Qué es.** Cómo una empresa crea, entrega y cobra valor. El **Lienzo de modelo de negocio** lo resume en nueve bloques.

| Bloque | Enlaza |
|---|---|
| Segmentos de clientes | instituciones privadas de cuidado de personas mayores (CDMX, luego Edomex, Jalisco, Nuevo León); centros públicos con plan Gobierno |
| Propuesta de valor | coordinación automática, en vivo, segura y con datos para decidir |
| Canales | venta directa, demostraciones, la página pública |
| Relación con clientes | suscripción, soporte, capacitación |
| Fuentes de ingreso | suscripción mensual por plan |
| Recursos clave | la plataforma, el equipo, los datos de referencia |
| Actividades clave | desarrollo, soporte, ventas |
| Socios clave | nube (hospedaje), instituciones piloto |
| Estructura de costos | sueldos (fijo), soporte y hospedaje (crecen con clientes), adquisición |

### SaaS y suscripción; MRR y ARPA

**Qué es.** [[SaaS]]: software como servicio, pagado por suscripción. **MRR**: ingreso recurrente mensual. **ARPA**: ingreso
promedio por cuenta (institución).

**En Enlaza.** Tres planes (Básico {{ neg.plan_basic_price }}, Profesional {{ neg.plan_professional_price }}, Institucional
{{ neg.plan_institutional_price }} al mes) con una mezcla supuesta: ARPA de {{ bm.arpa1 }}.

### Costos fijos y variables

**Qué es.** **Fijos:** no cambian con el número de clientes (sueldos, renta). **Variables:** crecen con los clientes.

**En Enlaza.** Fijo del año 1: {{ bm.fixed1 }} al mes. Variables: soporte y hospedaje, {{ bm.variable_cost }} por institución al
mes; más {{ bm.cac }} por cada institución nueva (adquisición).

### Punto de equilibrio

**Qué es.** Cuántos clientes (o cuánto tiempo) hacen falta para que los ingresos cubran los costos.

**Ejemplo.** Un puesto de tacos con renta de 10,000 al mes que gana 20 por taco necesita vender 500 tacos para no perder.

**En Enlaza.** Fórmula clásica: {{ bm.fixed1 }} ÷ {{ bm.arpa1 }} ≈ {{ bm.breakeven_static }}. Con el modelo mes a mes, deja de perder
dinero en el mes {{ bm.breakeven_month }}.

### Flujo de caja e inversión necesaria

**Qué es.** El dinero que entra y sale cada mes. La **inversión necesaria** es el punto más bajo de la caja acumulada:
lo que hay que financiar antes de recuperarse.

**En Enlaza.** {{ bm.investment }}, en el mes {{ bm.investment_month }}; recupera lo perdido en el mes {{ bm.payback_month }}.

### Valor del dinero en el tiempo, tasa de descuento y VPN

**Qué es.** Un peso hoy vale más que un peso dentro de cinco años (inflación, riesgo, oportunidad). La **tasa de descuento**
mide cuánto «castigamos» el futuro. El **[[VPN]]** suma los flujos futuros traídos a hoy: positivo = el proyecto crea valor a
esa tasa.

**Ejemplo.** Si te ofrecen 110 pesos dentro de un año o 100 hoy, y tu dinero puede rendir 10 % en otro lado, da igual: el
valor presente de esos 110 es 100.

**En Enlaza.** Tasa base {{ bm.rate_25 }} (tasa libre de riesgo + prima de empresa nueva). VPN: {{ bm.npv_15 }} al
{{ bm.rate_15 }}, **{{ bm.npv_25 }}** al {{ bm.rate_25 }}, {{ bm.npv_35 }} al {{ bm.rate_35 }}.

### Churn (cancelación)

**Qué es.** El porcentaje de clientes que se va cada mes. **En Enlaza:** {{ neg.monthly_churn }} % al mes (supuesto): vida
esperada de un cliente {{ bm.lifetime }}.

### LTV, CAC, LTV/CAC y recuperación del CAC

**Qué es.** **[[LTV]]**: lo que deja un cliente en toda su vida. **[[CAC]]**: lo que cuesta conseguirlo. **LTV/CAC** mayor que 3
se considera sano. **Recuperación del CAC**: meses de margen para pagar lo que costó conseguirlo.

**En Enlaza.** LTV {{ bm.ltv }}, CAC {{ bm.cac }}, **LTV/CAC {{ bm.ltv_cac }}**, recuperación en {{ bm.cac_payback }}.

### Tamaño de mercado (TAM, SAM, SOM)

**Qué es.** **TAM**: todo el mercado posible. **SAM**: la parte que tu producto puede atender. **SOM**: la parte que
realistamente puedes ganar.

**En Enlaza.** Medido con el [[DENUE]] (mayo de 2026): por ejemplo, {{ neg.denue_residences_private_cdmx }} residencias y
{{ neg.denue_day_centers_private_cdmx }} centros de día privados en la CDMX. Con el plan base, en el año 5 Enlaza tendría el
{{ bm.sc.base.share_cdmx }} de los privados de la CDMX: un SOM irreal. El escenario recomendado limita la participación al
{{ neg.recommended_private_cap }} % por entidad.

### Competencia

**Qué es.** Quién más resuelve el problema, y a qué precio. **En Enlaza:** software de consultorio (HuliPractice,
Doctoralia) cobra por médico; Enlaza cobra por institución e incluye la coordinación del personal (@ref(cap-negocio)).

### Escenarios y sensibilidad

**Qué es.** Probar el plan con supuestos distintos (pesimista, conservador, recomendado) y ver qué palanca mueve más el
resultado.

**En Enlaza.** Base (VPN {{ bm.sc.base.npv25 }}), conservador ({{ bm.sc.conservative.npv25 }}) y recomendado
({{ bm.sc.recommended.npv25 }}). ¿Qué haría el VPN base = 0? Precio Profesional {{ bm.zero_price }}, o {{ bm.zero_year5 }}
instituciones en el año 5, o CAC {{ bm.zero_cac }}.

## Por qué lo hicimos así

- **Suscripción y no comisión** ({{ neg.commission_alternative }} % evaluada): ingreso predecible y sin conflicto con instituciones
  de asistencia privada.
- **Supuestos en un CSV con fuente**, para que cualquier profesor pueda cambiar uno y ver el efecto en `/negocio`.
- **Mercado por segmento del DENUE**, no el total del sector.
- **Mostrar el VPN negativo** y proponer una alternativa, en lugar de inflar los supuestos.

## Dónde se ve en el sistema

| Concepto | Dónde |
|---|---|
| Planes y precios | página pública `/` (Planes) y `/negocio` |
| Equilibrio, VPN, LTV/CAC, escenarios | `/negocio` (Dirección); `business/model.ipynb` |
| Supuestos con fuente | `data/business/assumptions.csv` |
| Cálculo | `backend/app/services/business_model.py` |
| Uso real del prototipo | `/negocio` (servicios coordinados, horas ahorradas) |

## Números clave

{{ tabla bm.arpa1 bm.fixed1 bm.breakeven_static bm.breakeven_month bm.investment bm.npv_25 bm.ltv bm.cac bm.ltv_cac bm.cac_payback neg.monthly_churn bm.sc.recommended.npv25 neg.denue_residences_private_cdmx }}

## Limitaciones honestas

- Sin **entrevistas a clientes** ni prueba de disposición a pagar.
- Precios, mezcla, churn, CAC y crecimiento son **supuestos**.
- El **plan Gobierno** no tiene un precio de referencia público.
- No se calculó la **TIR** (tasa interna de retorno); el análisis usa VPN con tres tasas.
- Pesos nominales, antes de impuestos y sin IVA.

## Qué decir en 2 minutos

!!! frase "Guion de 2 minutos · Emprendimiento"
    «Nuestro cliente es la institución que cuida personas mayores: hoy coordina visitas con WhatsApp y hojas de cálculo.
    Enlaza es un **SaaS por suscripción**: tres planes por tamaño, ingreso promedio de {{ bm.arpa1 }} al mes por institución.

    Con un costo fijo de {{ bm.fixed1 }} al mes, el **punto de equilibrio** clásico es de {{ bm.breakeven_static }}; con el modelo
    mes a mes dejamos de perder dinero en el mes {{ bm.breakeven_month }}. Cada cliente es muy rentable: **LTV/CAC de
    {{ bm.ltv_cac }}** y recuperamos su costo de adquisición en {{ bm.cac_payback }}.

    Pero somos honestos: al {{ bm.rate_25 }} de descuento el **VPN del plan base es negativo** ({{ bm.npv_25 }}), y medimos el
    mercado real con el **DENUE**: el plan base pediría quedarnos con el {{ bm.sc.base.share_cdmx }} de los establecimientos privados de la CDMX. Por eso
    proponemos un **escenario recomendado**: tope de participación, expansión a otros estados y un plan para centros públicos;
    su VPN es {{ bm.sc.recommended.npv25 }}, y decimos de qué supuestos depende.»

## 10 preguntas difíciles

!!! pregunta "1. ¿Quién paga y quién usa?"
    Paga la institución; usan coordinación, personal, médicos y familias. La familia no paga a Enlaza.

!!! pregunta "2. ¿Por qué suscripción y no comisión por servicio?"
    La suscripción da ingreso predecible a Enlaza y costo predecible a la institución. Una comisión por servicio cobraría más a
    quien atiende más, lo que choca con instituciones de asistencia privada.

!!! pregunta "3. ¿De dónde salen los precios?"
    Son supuestos, comparados con el software de consultorio (HuliPractice de {{ neg.competitor_hulipractice_min }} a
    {{ neg.competitor_hulipractice_max }} por médico). Enlaza cobra por institución e incluye la coordinación del personal. Falta
    validarlos con entrevistas.

!!! pregunta "4. Si el VPN es negativo, ¿por qué invertir?"
    Al {{ bm.rate_25 }} el plan base no crea valor: las pérdidas de los primeros años pesan más que las utilidades del final.
    Por eso proponemos el escenario recomendado (VPN {{ bm.sc.recommended.npv25 }}), y decimos que depende del plan Gobierno y del
    recorte de sueldo a los fundadores el primer año.

!!! pregunta "5. ¿Qué es LTV/CAC y por qué el suyo es tan alto?"
    Lo que deja un cliente en su vida contra lo que cuesta conseguirlo. Es alto ({{ bm.ltv_cac }}) porque el churn supuesto es
    bajo ({{ neg.monthly_churn }} % al mes) y el costo variable por cliente es pequeño. Si el churn fuera mayor, bajaría: es un
    supuesto a validar.

!!! pregunta "6. ¿Qué tan grande es el mercado?"
    Lo medimos con el DENUE por clase de actividad: residencias, centros de día y enfermería a domicilio, privados y públicos.
    Por ejemplo, {{ neg.denue_residences_private_cdmx }} residencias privadas en la CDMX. Es pequeño: por eso hay que crecer a otras
    entidades y a centros públicos.

!!! pregunta "7. ¿Qué tasa de descuento usaron y por qué?"
    {{ bm.rate_25 }} nominal: tasa libre de riesgo (TIIE 28 días {{ neg.tiie_28_days }} %) más una prima por ser empresa nueva.
    Mostramos también {{ bm.rate_15 }} y {{ bm.rate_35 }} para ver la sensibilidad.

!!! pregunta "8. ¿Cuánto dinero necesitan?"
    {{ bm.investment }} en el plan base (el punto más bajo de la caja, en el mes {{ bm.investment_month }}); en el recomendado,
    {{ bm.sc.recommended.investment }}.

!!! pregunta "9. ¿Qué los diferencia de la competencia?"
    La competencia cobra por médico y se centra en el consultorio. Enlaza es para la institución: asigna personal a domicilio
    respetando turnos y ley, tiene tablero en vivo, avisa a familias, detecta emergencias por voz y separa los datos por
    institución.

!!! pregunta "10. ¿Qué supuesto es el más débil?"
    El precio del plan Gobierno (no encontramos referencia pública) y la disposición a pagar de las instituciones privadas.
    Los dos se validarían con entrevistas y un piloto.
