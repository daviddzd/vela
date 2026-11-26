# Las 20 preguntas más probables {#guia-preguntas}

Respuesta corta; la larga está en el capítulo indicado.

!!! pregunta "1. ¿Qué es Enlaza en una frase?"
    Una plataforma web por suscripción para que las instituciones que cuidan personas mayores coordinen visitas: asigna sola a
    quien puede ir y llega antes, lo delicado lo aprueba una persona, todos lo ven en vivo, y un asistente de voz detecta
    emergencias. @ref(cap-que-es)

!!! pregunta "2. ¿Por qué datos sintéticos?"
    Porque los datos de salud son sensibles (LFPDPPP 2025) y un proyecto escolar público no debe tenerlos. Los generamos calibrados
    con el Censo, la ENSANUT y la ENASEM: las proporciones se parecen a la realidad, las personas no existen. @ref(cap-datos)

!!! pregunta "3. ¿Cómo evitan que una institución vea los datos de otra?"
    Con seguridad por fila en PostgreSQL: la API se conecta con un usuario que no es dueño de las tablas y fija la institución en
    cada petición; sin institución ve {{ db.rls_patients_none }} filas. Un intento ajeno responde 403 y queda en la bitácora.
    @ref(cap-seguridad)

!!! pregunta "4. ¿La máquina decide todo?"
    No. Lo rutinario se asigna solo; lo de prioridad alta lo aprueba una persona. Solo lo urgente sin respuesta en
    {{ cfg.auto_apply_after }} se aplica con aviso y se puede cambiar. @ref(cap-operacion)

!!! pregunta "5. ¿Cómo eligen a quién mandar?"
    Quien tiene la habilidad, está en turno, no es su día de descanso y no tiene otra visita que se cruce; entre ellos, quien llega
    antes con el tráfico de esa hora. La cola va por prioridad, riesgo y espera. @ref(cap-operacion)

!!! pregunta "6. ¿Qué pasa si falla el internet?"
    Todo corre en la laptop; solo se pierden el enlace público y las calles del mapa. Seguimos en `localhost:8080`. @ref(cap-planb)

!!! pregunta "7. ¿Qué pasa con una falsa alarma de voz?"
    Si la detecta solo el clasificador, sale un aviso ámbar (no la pantalla roja) y coordinación llama a la familia; si nadie
    responde en {{ cfg.escalate_after }}, se escala a Dirección. Preferimos una falsa alarma revisada a una emergencia perdida.
    @ref(cap-voz)

!!! pregunta "8. ¿Qué tan bueno es el asistente de voz?"
    En el holdout a ciegas detectó {{ voz.holdout.sens }} de las emergencias con {{ voz.holdout.fa100 }} falsas alarmas por 100 notas.
    No presumimos la prueba interna porque esos datos se usaron para construirlo. @ref(cap-voz)

!!! pregunta "9. ¿El modelo de lenguaje diagnostica?"
    No: resume lo dicho en un formato fijo, con filtro de frases prohibidas, y el nivel lo ponen las reglas y el clasificador.
    @ref(cap-voz)

!!! pregunta "10. ¿Cómo validaron la simulación?"
    Con las reglas de antes, el modelo reproduce el «sin atender» del historial en servicios cortos ({{ sim.val_sim_short_pct }} contra
    {{ sim.val_real_short_pct }}); con turnos largos difiere y sabemos por qué. @ref(cap-sirag)

!!! pregunta "11. ¿Por qué Friedman y no ANOVA?"
    Porque las políticas se prueban sobre las mismas réplicas (números aleatorios comunes): son muestras pareadas, y casi nunca
    normales. @ref(cap-m-sim)

!!! pregunta "12. ¿Qué cambió en el producto por la simulación?"
    El límite de tiempo para lo urgente y la reserva del candidato: con una coordinación lenta, lo urgente esperaba más que con un
    despachador humano. @ref(cap-bitacora)

!!! pregunta "13. ¿Cuánto cuesta y cuándo es rentable?"
    {{ bm.arpa1 }} al mes de ingreso promedio por institución; deja de perder dinero en el mes {{ bm.breakeven_month }}; el VPN base al
    {{ bm.rate_25 }} es {{ bm.npv_25 }} y el del escenario recomendado {{ bm.sc.recommended.npv25 }}. @ref(cap-negocio)

!!! pregunta "14. ¿Qué tan grande es el mercado?"
    Lo medimos con el DENUE por segmento: por ejemplo, {{ neg.denue_residences_private_cdmx }} residencias privadas en la CDMX. El plan
    base no cabe; por eso el escenario recomendado limita la participación y crece por regiones. @ref(cap-m-emp)

!!! pregunta "15. ¿Cómo cumplen la ley de datos personales?"
    Tres consentimientos con firma y vencimiento (y el asentimiento de la persona), aviso de privacidad, ARCO con los plazos de ley,
    seguridad por fila y bitácora; sin consentimiento, la API bloquea la función. @ref(cap-etica)

!!! pregunta "16. ¿Y la Ley Federal del Trabajo?"
    Descanso semanal (art. 69), tipo de jornada por horas (art. 60), máximos (art. 61) y relevos; los nocturnos que exceden la ley se
    marcan y se avisan. @ref(cap-operacion)

!!! pregunta "17. ¿Cómo responde Enlaza al incidente crítico del Problema Prototípico?"
    La contingencia se ve por estación (no promediada), el despachador prioriza riesgo y tráfico de la hora, una sola base reasigna
    sin copiar datos, la voz declara su sesgo, el consentimiento se exige en la API y el plan de negocios crece por regiones.
    @ref(cap-m-pp-doc)

!!! pregunta "18. ¿Qué cambió desde el Avance 2?"
    La asignación pasó de sugerida a automática con aprobación humana en lo delicado; más instituciones; 403 en vez de 404;
    duplicados rechazados con motivo; y se agregaron voz, simulación, contingencia, ley laboral y negocio. @ref(cap-avance2)

!!! pregunta "19. ¿Ustedes programaron esto?"
    El problema, el diseño, las reglas, las decisiones y la revisión son del equipo; la mayor parte del código la escribió un
    asistente de programación con IA (Claude Code) bajo esas reglas, con un PR por cambio y pruebas. Podemos defender cada parte.
    @ref(cap-construccion)

!!! pregunta "20. ¿Qué no funciona o falta?"
    Las falsas alarmas de voz, la evaluación con hablantes reales, el diagnóstico de campo (se hace esta semana), los respaldos
    automáticos y la prueba con una institución real. Lo decimos en cada capítulo, en «Limitaciones honestas».
