# Números que hay que saberse {#guia-numeros}

Generada al compilar el libro: cada valor sale de su archivo (columna «Fuente»). Si un profesor pregunta «¿de dónde sale?», la
respuesta está en esa columna.

## El mundo sintético

{{ tabla seed.pop60_cdmx seed.persons seed.institutions seed.patients seed.caregivers seed.service_requests seed.requests_unattended_pct seed.broad_multimorbidity_pct cal.ref_multimorbidity }}

## Seguridad y operación

{{ tabla db.rls_patients_none db.rls_patients_insa db.rls_patients_all cfg.auto_apply_after cfg.urgent_within cfg.hold_minutes cfg.late_tolerance code.min_visits_rate repo.tests_summary }}

## SIRAG-D

{{ tabla sim.runs_main cfg.replications sim.normal.vela_timeout.high_wait_p90_min sim.normal.human_dispatcher.high_wait_p90_min sim.normal.vela_timeout.crisis_response_p90_min sim.normal.vela_timeout.unattended_pct sens.extra_staff.targeted.vela_timeout.unattended_pct sim.val_real_short_pct sim.val_sim_short_pct }}

## Enlaza Voz

{{ tabla voz.holdout.n voz.holdout.sens voz.holdout.sens_rules voz.holdout.fa100 vozb.holdout.red vozb.holdout.red_false vozb.holdout.amber vozb.holdout.amber_false vozv2.v2.sens }}

## Negocio

{{ tabla bm.arpa1 bm.fixed1 bm.breakeven_static bm.breakeven_month bm.npv_25 bm.sc.base.tir bm.ltv_cac bm.sc.recommended.npv25 bm.sc.recommended.tir neg.denue_residences_private_cdmx }}
