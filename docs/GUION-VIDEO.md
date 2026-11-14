# Guion para grabar la demostración

Duración sugerida: 2 a 4 minutos. Grabar el panel y, si se desea, cambiar a las
pestañas de GitHub y de Argo CD. Las voces de los expositores pueden añadirse
durante una grabación nueva o después de revisar el ejemplo.

| Escena | Acción visible | Explicación sugerida |
|---|---|---|
| 1. Inicio | Git=2, Deployment=2 y dos Pods Ready | Este laboratorio ejecuta una página real en Kubernetes. Git contiene la configuración deseada y Argo CD la compara con el clúster. |
| 2. Repositorio | Abrir deployment.yaml y observar replicas: 2 | Este número no se configura en el panel: está versionado en Git. |
| 3. Commit | Pulsar Publicar 3 réplicas y mostrar el commit | Publicamos un cambio en GitHub. Argo CD detecta el nuevo commit y sincroniza. El panel no aplica este Deployment. |
| 4. Resultado | Esperar tres Pods Ready | Kubernetes ejecuta ahora tres réplicas, de acuerdo con lo declarado en Git. |
| 5. Desvío | Desactivar selfHeal y cambiar a dos | Desactivamos selfHeal para ver la diferencia con claridad. Modificamos el Deployment directamente. Git sigue declarando tres. |
| 6. Comparación | Mostrar Git=3, Deployment=2 y OutOfSync | El estado real ya no coincide con el repositorio. Auto-sync está habilitado, pero no corrige este cambio del mismo commit mientras selfHeal está desactivado. |
| 7. Reparación | Activar selfHeal y esperar tres Pods | Activamos selfHeal. Argo CD vuelve a aplicar el estado de Git y Kubernetes recupera tres réplicas. |
| 8. Cierre | Synced y Healthy | Git define el objetivo, Argo CD lo reconcilia y Kubernetes ejecuta. Borrar un Pod sería otra prueba: esa recuperación la hace el ReplicaSet. |

## Preparación de una toma nueva

1. Ejecutar `scripts/Start-Lab.ps1` si Docker o el panel estaban apagados.
2. Pulsar **Preparar otra demostración** y esperar dos Pods Ready.
3. Grabar solamente el panel, GitHub y la interfaz local de Argo CD.
4. Evitar ventanas de credenciales. No es necesario mostrar tokens, contraseñas ni kubeconfig.
5. Conservar el tiempo de espera real de reconciliación o señalar cualquier corte de edición.

La comparación se obtiene de un clúster real, no de una animación de réplicas.
El video de ejemplo que se entregue se identifica por separado de este guion.
