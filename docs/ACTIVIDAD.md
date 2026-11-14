# Actividad: ¿quién manda, Git o el cambio manual?

Duración sugerida: 6 a 8 minutos. Para 24 compañeros: seis grupos de cuatro.
El presentador utiliza el laboratorio; los grupos observan, predicen y explican.
No necesitan instalar herramientas en los 24 dispositivos.

## Objetivo

Comprobar cómo Argo CD sincroniza un Deployment con Git y cómo cambia el resultado
al activar `selfHeal`. Distinguir la reconciliación de Argo CD de la recuperación de Pods
que ya hace Kubernetes.

## Material

Laboratorio iniciado, panel proyectado y acceso al repositorio GitHub. La página
debe mostrar dos réplicas en Git y dos Pods Ready antes de empezar.

## Desarrollo

1. **Estado inicial, un minuto.** Mostrar `deployment.yaml`, `replicas: 2` y el estado
   `Synced / Healthy`. Abrir la página real para comprobar que responde.
2. **Cambio desde Git, un minuto.** Preguntar qué ocurrirá al publicar `replicas: 3`.
   Pulsar la primera acción. Mostrar el nuevo commit y esperar tres Pods Ready.
   No aplicar el Deployment con kubectl.
3. **Desvío manual, un minuto.** Avisar que se desactivará temporalmente `selfHeal`
   para observar el resultado. Pulsar la segunda acción. Git conserva tres réplicas;
   el Deployment pasa a dos y Argo CD muestra `OutOfSync`.
4. **Predicción de los grupos, un minuto.** Cada grupo escribe qué valor debe
   permanecer en Git, qué valor se observa ahora y qué componente puede corregirlo.
5. **Reparación, un minuto.** Activar `selfHeal` con la tercera acción.
   Observar que Argo CD restablece tres réplicas y vuelve a `Synced / Healthy`.
6. **Comprobación adicional, un minuto.** Repetir el cambio manual con `selfHeal`
   ya activo. La corrección puede ser rápida; el registro conserva los cambios observados.

## Evidencia para el punto extra

Entregar una captura o una explicación breve que contenga:

- El commit que cambió las réplicas a tres.
- La diferencia Git=3 y Deployment=2 con `selfHeal` desactivado.
- El estado final de tres Pods Ready y `Synced / Healthy` con `selfHeal` activo.
- Una frase que explique por qué borrar un Pod no habría demostrado lo mismo.

El docente decide cómo asignar el punto. Esta guía no presupone una calificación.

## Resultado esperado

Git permanece en tres durante el desvío y su reparación. Argo CD corrige el
Deployment; Kubernetes materializa ese objetivo ejecutando los Pods.
`Synced` indica que la configuración coincide con Git. `Healthy` evalúa la salud
de los recursos; son comprobaciones distintas.
