# code_review_v37

## Alcance
Revisión enfocada en v36: verifiqué si lo que figuraba como abierto en P2 quedó resuelto, si quedaron cierres frágiles, y si hay pendientes nuevos o heredados. No se ejecutaron pruebas.

## Resumen de estado de v36 (seguimiento)

### V36 issues P2 verificados como resueltos en este estado
- `v36-P2-01` (`narrow()` sin límite): lazos de bounding ahora tienen límite y arrojan `ContradictionError` en contradicciones reales.
  - [forge/src/boxscore_forge/bounds.py:103](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_forge/bounds.py:103)

- `v36-P2-02` (validación asimétrica constructor/parse): validación de patrón y perfil ahora está en rutas comunes.
  - [forge/src/boxscore_package/format.py:194](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py:194)
  - [forge/src/boxscore_package/format.py:968](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py:968)

- `v36-P2-04` (hook pre-push por rama activa): el hook ahora lee refs de stdin y bloquea push hacia `refs/heads/main`.
  - [.githooks/pre-push:36](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/.githooks/pre-push:36)

- `v36-P2-08` (comparación puzzle/solución): se verifica explícitamente que cada `given` coincide con `solution`.
  - [forge/src/boxscore_package/format.py:1079](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py:1079)

- `v36-P2-10` (metadata leak antes de publicación): existe check de leak en el gate y se publica con `published()`.
  - [forge/src/boxscore_verify/certify.py:314](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_verify/certify.py:314)
  - [forge/scripts/write_reference_puzzles.py:232](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/scripts/write_reference_puzzles.py:232)

- `v36-P2-11` (SQL con valores de BD en una query con `S608` injustificado): consulta de excepción en batting-order ahora parametriza valores de BD.
  - [discovery/batting-order/measure.py:366](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/batting-order/measure.py:366)

- `v36-P2-12` (provenance fallback en metadata): la decisión de lineage (`lineup`) se conserva en metadata publicada.
  - [forge/scripts/write_reference_puzzles.py:215](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/scripts/write_reference_puzzles.py:215)

- `v36-P2-15` (doble convención de innings): parse/conversión centralizada y explícita en Python y JS.
  - [forge/src/boxscore_package/innings.py:16](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/innings.py:16)
  - [serve/engine/columns.js:80](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/serve/engine/columns.js:80)

- `v36-P2-16` (outs de staff como múltiplo de 3): validación de rango correcto para 2/3/4outs y extremos de entrada.
  - [forge/src/boxscore_verify/certify.py:386](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_verify/certify.py:386)

### Issue mal cerrado de v36 (persiste)

- `v37-P3-01` (reapertura de `v36-P2-06`): la garantía del tutorial aún depende de una sola condición fuerte y frágil de conjunto.
  - **Archivo:** [forge/scripts/write_reference_puzzles.py:330](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/scripts/write_reference_puzzles.py:330)
  - **Severidad:** P3
  - **Qué pasa:** hoy el gate comprueba sólo que exista al menos una publicación con referencia suprimida por juego (`5a/5b`) y otra con footnote vivo. La verificación corrige el bug absoluto de `v36-P2-06`, pero sigue permitiendo una sola instancia de cada caso. En el estado actual esto es frágil para el objetivo editorial: la cobertura tutorial depende de una muestra de 6 y de la suerte de descarte por `target`.
  - **Impacto:** si se cambia el perfil de candidatos en el futuro (cambio de `CEILING`, nuevas reglas de filtrado, fuente de `sample`), la condición de tutorial puede colapsar sin un fallo de cobertura explícito más allá de lo mínimo.
  - **Sugerencia:** en `build`/`_choose` o `_traits_survived`, exigir explícitamente que el lote publicado conserva casos distintos por característica con umbrales mínimos de redundancia (ej. al menos dos ejemplos distribuidos por origen/decada), o registrar una métrica de calidad de tutorial en manifest.

### Pendientes (pendientes de resolver)

- `v36` deja en estado abierto `P3: 44, none started` en su sección final.
  - Referencia: [docs/reviews/code_review_v36.md:1550](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/docs/reviews/code_review_v36.md:1550)
  - Esto significa que, fuera de `v36-P2-06`, se mantiene sin avanzar el bloque de riesgo de baja severidad/QA frente a `compose`, `hook`, UI, scripts y hardening operativo.

## Nuevos issues detectados en v37

- **Ningún issue P0/P1/P2 nuevo de alta severidad** adicional detectado en esta pasada.
- El único hallazgo accionable adicional es la reapertura controlada de `v36-P2-06` como `v37-P3-01`.
