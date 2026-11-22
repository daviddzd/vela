# Decisiones técnicas · pasos 1 y 2 (infraestructura, sesión, aislamiento y bitácora)

Rama `feature/base-api`. Este documento explica *por qué* se hizo así, para responder preguntas en la
defensa (en especial: "¿cómo se evita que una institución vea a otra?").

## 1. ¿403 o 404 cuando alguien pide un paciente de otra institución?

**Decisión: respondemos 403 ("pertenece a otra institución") y lo registramos en `audit_log`.**

- El aislamiento lo hace **PostgreSQL**, no el código de la API: con seguridad a nivel de fila (RLS),
  la cuenta `vela_api` simplemente *no ve* las filas de otra institución. Aunque hubiera un error en
  el código, la base no entregaría el dato (falla cerrada: sin `app.institution_id` → 0 filas).
- Pero eso tiene un efecto: para la API, un paciente de otra institución es igual a uno que no existe
  y solo podría responder **404**. Con un 404 no sabríamos que hubo un intento de acceso indebido.
- El criterio de aceptación A2 y el principio de trazabilidad (`docs/spec/11`) piden lo contrario:
  **distinguir el intento y dejarlo registrado** para que la institución pueda auditarlo.
- Alternativa descartada: responder 404 siempre (oculta incluso que el identificador existe). Es útil
  en sistemas públicos para no revelar información, pero aquí quien pregunta ya es un usuario
  autenticado de una institución cliente, el identificador (`PAC-0151`) no contiene datos personales,
  y es más valioso para la institución saber que alguien lo intentó.
- Si el paciente no existe en ninguna institución, sí respondemos 404.

## 2. ¿Por qué existe la función `entity_institution`?

Para responder 403 la API necesita saber **a qué institución pertenece** un identificador que RLS le
oculta. Opciones que consideramos:

| Opción | Problema |
|---|---|
| Conectar la API como dueño de las tablas | Se salta RLS en todo: un error en el código expondría todo. |
| Codificar la institución en el identificador | Los ID de la semilla no la tienen y sería frágil. |
| **Función `SECURITY DEFINER` mínima** | Elegida: corre con permisos del dueño, pero devuelve **solo** el `institution_id`. |

Cómo la hicimos segura (migración `backend/migrations/versions/0001_entity_institution.py`):

- Devuelve únicamente el `institution_id` (por ejemplo `INS-B`), nunca nombre, salud ni otra columna.
- **Lista fija de entidades** con `CASE`: hoy solo `'patient'`. Cualquier otro valor devuelve `NULL`,
  sin error y sin SQL dinámico (no hay forma de inyectar consultas).
- `SET search_path = public, pg_temp`: nadie puede crear una tabla falsa `patients` en otro esquema
  para engañarla. `pg_temp` va al final porque, si no se menciona, PostgreSQL lo revisa *primero* para
  tablas; así un objeto temporal nunca puede reemplazar a los nuestros. Además las tablas van con
  esquema explícito (`public.patients`).
- `REVOKE ALL ... FROM PUBLIC` y `GRANT EXECUTE` **solo** a `vela_api`.
- Hay pruebas que lo comprueban (`backend/tests/test_tenant_isolation.py`).

Flujo de `GET /api/patients/{id}`:
1. Busca el paciente con la sesión limitada a la institución del usuario (RLS).
2. Si no aparece, pregunta `entity_institution('patient', id)`.
3. Si pertenece a otra institución → registra `blocked_cross_tenant` en **una transacción propia**
   (para que quede guardado aunque la petición falle) y responde 403.
4. Si no existe → 404. Si aparece → registra `read_patient` y responde 200.

## 3. Sesión y transacción por petición

- En cada petición la API abre **una** transacción y ejecuta
  `SELECT set_config('app.institution_id', '<id>', true)`. Es lo mismo que `SET LOCAL`, pero acepta
  el valor como parámetro (evita inyección). El valor muere al terminar la transacción, así que nunca
  pasa a la siguiente petición que reutilice la conexión (hay una prueba de esto).
- `owner` (Dirección Vela) usa `'*'`, que las políticas entienden como "todas las instituciones".
- `users` y `audit_log` no tienen RLS: el inicio de sesión tiene que encontrar al usuario antes de
  saber su institución, y la bitácora es de toda la plataforma.

## 4. Inicio de sesión

- Contraseñas con **bcrypt**, verificadas contra los hashes `$2a$` de la semilla.
- **JWT** firmado (HS256, 8 h) con `user_id`, `role` e `institution_id`, guardado en una cookie
  `httpOnly` (JavaScript no puede leerla), `SameSite=Lax` y `Secure` cuando la URL pública es https.
- El token **no basta**: en cada petición se revisa en la base que el usuario siga activo y con el
  mismo rol e institución. Si se desactiva a alguien, pierde el acceso en la siguiente petición.
- Límite de **5 intentos fallidos por minuto por IP**. Solo cuentan los fallidos: en la defensa muchas
  personas entran desde la misma red (misma IP pública) y un inicio correcto no debe bloquearse.
- Mismo mensaje para correo inexistente y contraseña incorrecta (no revela qué cuentas existen).

## 5. Roles y pantallas

El mapa rol → pantallas está en un solo lugar (`backend/app/core/roles.py`). La API lo envía al
frontend en `/api/auth/me` y además valida el rol en cada endpoint (`require_role`): ocultar un botón
no es seguridad, la API siempre vuelve a revisar.

Pantalla inicial: `owner` → `/panorama`, `coordinator` → `/tablero`, `physician` → `/reportes-voz`,
`caregiver` → `/mis-visitas`, `family` → `/familia`.

**Pendiente del paso 3** (anotado como `TODO` en el código): hoy médico y cuidador ven toda su
institución; después solo verán a sus propios pacientes y visitas.

## 6. Migraciones y permisos

- **Línea base** = `database/sql/001–005`, que carga `infra/db-init.sh` la primera vez.
  La primera migración de Alembic (`0001`) solo agrega `entity_institution`.
- Las migraciones corren en un servicio aparte de un solo uso (`migrate`), como dueño de las tablas.
  Así **solo `db` y `migrate` conocen la contraseña del dueño**; `api` y `worker` solo tienen la de
  `vela_api`. (En el plan se propuso correrlas dentro de `api`; separarlas reduce lo que ve la API.)
- `ALTER DEFAULT PRIVILEGES` en `db-init.sh`: las tablas que creen migraciones futuras darán
  automáticamente `SELECT, INSERT, UPDATE` a `vela_api`, y las funciones nuevas **no** serán
  ejecutables por cualquiera (cada migración da `GRANT EXECUTE` explícito). La RLS de cada tabla nueva
  de una institución se agrega a mano en su migración.
- `vela_api` no puede modificar ni borrar `audit_log` (bitácora de solo agregar).

## 7. Un solo puerto público

Caddy en `localhost:8080`: `/api/*` y `/ws/*` → FastAPI (sin quitar el prefijo, porque FastAPI ya usa
`/api` y `/ws`), todo lo demás → la app de React. `/ws/ping` existe solo para comprobar que el paso de
WebSocket funciona antes del tablero en vivo (paso 4).

## Cómo comprobarlo

```bash
docker compose down -v && docker compose up -d --build   # desde cero
curl http://localhost:8080/api/health
python scripts/verify_db.py
docker compose exec api pytest -q
```
