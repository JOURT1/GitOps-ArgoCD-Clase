# GitOps con Argo CD: demostración de clase

Actividad práctica para acompañar la exposición de Argo CD y grabar un video.
Usa un repositorio GitHub real, Argo CD y Kubernetes local. El cuestionario es
una dinámica independiente; esta práctica demuestra el despliegue y la corrección de desvíos.

## Qué se demuestra

1. Git declara dos réplicas y Kubernetes ejecuta dos Pods.
2. Un commit cambia `spec.replicas` de dos a tres. Argo CD lee Git y actualiza el Deployment.
3. Se desactiva temporalmente `selfHeal` y se cambia el Deployment manualmente a dos.
   Git continúa declarando tres. Argo CD muestra `OutOfSync`.
4. Al activar `selfHeal`, Argo CD vuelve a aplicar las tres réplicas declaradas en Git.
5. Un segundo cambio manual con `selfHeal` activo permite comprobar la reparación automática.

**Borrar un Pod no es la prueba de selfHeal de Argo CD.** En ese caso, el ReplicaSet de
Kubernetes crea otro Pod. Aquí se cambia el valor de `Deployment.spec.replicas`,
que Kubernetes por sí solo conservaría en dos si nadie lo reconciliara con Git.

## Ejecutar en Windows

Requisitos: PowerShell 7, Docker Desktop con contenedores Linux, Git con permiso de push a este repositorio,
Python 3 y kubectl. El script reutiliza kind si existe en el laboratorio anterior o
descarga su binario oficial verificando SHA256.

```powershell
git clone https://github.com/JOURT1/GitOps-ArgoCD-Clase.git
cd GitOps-ArgoCD-Clase
.\scripts\Start-Lab.ps1
```

| Pantalla | Dirección local |
|---|---|
| Panel de la actividad y botones | http://127.0.0.1:14590 |
| Interfaz original de Argo CD | http://127.0.0.1:14580 |
| Página desplegada en Kubernetes | http://127.0.0.1:14500 |

El panel consulta los recursos reales con kubectl y el último commit de `origin/main`.
Sus botones ejecutan commit/push, cambios explícitos en la política de la Application
y un escalado manual del Deployment. **El panel nunca ejecuta la reconciliación**:
esa tarea la realiza Argo CD.

Las acciones publican commits reales en `main`. Solo el presentador necesita permiso
de escritura; los compañeros pueden mirar la demostración y explicar el resultado.
Para otro repositorio, adapta las URL de `argocd/` y la constante `REPOSITORY` del panel.

## Actividad y grabación

- [Video de la demostración real, MP4](output/video/Demostracion-GitOps-ArgoCD.mp4): 3 min 38 s,
  sin narración y con subtítulos en español.
- [Actividad para el punto extra](docs/ACTIVIDAD.md)
- [Guion del video](docs/GUION-VIDEO.md)
- [Comandos equivalentes al panel](docs/COMANDOS.md)
- [Evidencias de la ejecución](output/evidencia.json), una vez generado el archivo

La grabación muestra el panel conectado al clúster, el manifiesto de GitHub,
la interfaz original de Argo CD y una página servida por un Pod real.
Se construyó con capturas periódicas del navegador y conserva sus intervalos medidos.
Los subtítulos identifican cada paso. Pueden usarla como ejemplo o grabar una toma
nueva con sus propias voces siguiendo el guion.

La ejecución verificada aprobó diez comprobaciones: estado inicial, publicación de
un nuevo commit, despliegue de su revisión, tres Pods Ready, desvío manual,
persistencia del desvío sin selfHeal, reparación, segunda reparación con selfHeal activo,
respuesta HTTP 200 desde un Pod y preparación de una nueva toma.
El [estado final grabado](output/video/estado-final-grabado.json) conserva el commit
de tres réplicas usado en el video. Al terminar se volvió a dos réplicas mediante otro commit.

Antes de cada repetición pulsa **Preparar otra demostración** y espera a ver
Git=2, Deployment=2, dos Pods Ready y `Synced / Healthy`.

## Alcance del laboratorio

Clúster independiente `gitops-clase`, namespace de aplicación `demo-clase`, Kubernetes
v1.32.2 y Argo CD v3.4.13. Las versiones están fijadas para poder repetir la práctica.
No despliega SARSEG ni modifica los clústeres de la práctica P2. La imagen de Nginx
ya está construida: la compilación y un pipeline de CI quedan fuera de esta actividad.

Los puertos se publican solamente en `127.0.0.1`. La interfaz local de Argo CD permite
lectura anónima para grabar sin mostrar contraseñas, con el rol `readonly`.
La configuración HTTP y de lectura anónima es exclusiva de este laboratorio local.
El kubeconfig y los logs permanecen en `.local/`, fuera de Git. No se guardan tokens de GitHub.

## Referencias

- [Instalación oficial de Argo CD](https://argo-cd.readthedocs.io/en/stable/getting_started/)
- [Sincronización automática y selfHeal](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Compatibilidad de Argo CD 3.4 con Kubernetes](https://argo-cd.readthedocs.io/en/release-3.4/operator-manual/tested-kubernetes-versions/)
- [kind: configuración de puertos locales](https://kind.sigs.k8s.io/docs/user/configuration/)
