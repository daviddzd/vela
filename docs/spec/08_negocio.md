# 08 · Modelo de negocio (Emprendimiento)

Supuestos y fuentes en `data/business/assumptions.csv`. La página `/negocio` y un cuaderno
`business/model.ipynb` calculan todo a partir de ese archivo.

## Modelo: suscripción mensual (SaaS)
| Plan | Pacientes | Precio MXN/mes |
|---|---|---|
| Básico | hasta 50 | 2,500 |
| Profesional | hasta 150 | 6,000 |
| Institucional | sin límite | 12,000 |

Referencia de mercado: software de consultorio como HuliPractice cuesta de 490 a 2,540 MXN/mes por
profesional; Vela cobra por institución e incluye coordinación de personal. Alternativa evaluada y descartada
como principal: comisión de 5 % por servicio (ingreso variable y conflicto con instituciones de asistencia privada).

## Mercado
CDMX: 1,491,619 personas de 60+ (Censo 2020); 109 asilos y 319 establecimientos de cuidado residencial
(DENUE); 174 residencias de la Junta de Asistencia Privada (2020). Expansión: CDMX → Edomex conurbado →
Jalisco → Nuevo León.

## Cálculo base (para la exposición)
- Mezcla de planes (**supuesto**): 40 % Básico, 45 % Profesional, 15 % Institucional →
  ingreso promedio por institución ≈ **5,500 MXN/mes**.
- Costo fijo mensual año 1: 4 fundadores × 17,678 MXN × 1.35 (carga patronal) + 3,000 infraestructura
  ≈ **98,500 MXN/mes**.
- Punto de equilibrio ≈ 98,500 / 5,500 ≈ **18 instituciones**.
- Clientes: 5 (año 1) → 15 → 30 → 50 → 75 (año 5), cancelación 1.5 % mensual → el equilibrio se cruza en el año 3.
- VPN a 5 años con tasa de descuento 25 % (sensibilidad 15 % y 35 %); referencia: tasa objetivo Banxico
  6.25 %, TIIE 28 días 6.5147 %, inflación anual 3.75 % (oct 2026).

## Métricas que muestra el sistema (dato real del uso del prototipo)
Servicios coordinados por institución, % sin atender antes/después, horas de coordinación ahorradas
(supuesto: 3 min por asignación manual evitada), ingreso recurrente mensual (MRR) simulado.
