# Guía: Cómo Formular Queries Efectivas

**Versión**: 1.2.0
**Fecha**: 2025-10-28
**Audiencia**: Usuarios del Sistema RAG

---

## 📋 Introducción

Esta guía te ayudará a formular queries (preguntas) que obtengan mejores resultados del sistema RAG. El sistema es capaz de manejar desde preguntas simples hasta preguntas complejas con razonamiento multi-hop, pero la **formulación de la query** es clave para obtener buenos resultados.

---

## 1️⃣ Tipos de Queries

### ✅ Queries Simples (Single-hop)

**Características:**
- Una sola pregunta directa
- Respuesta en 1-2 fuentes
- Rápidas (3-5 segundos)
- No requieren razonamiento multi-paso

**Ejemplos:**
```
✓ ¿Qué es un OCAD?
✓ Define proyecto de inversión
✓ ¿Qué es el Sistema General de Regalías?
✓ ¿Cuál es la vigencia del acuerdo?
```

**Cuándo usar:**
- Definiciones
- Conceptos específicos
- Información puntual

---

### 🚀 Queries Complejas (Multihop)

**Características:**
- Requieren múltiples pasos de razonamiento
- Información de varias fuentes no adyacentes
- Más lentas (8-15 segundos)
- Sistema descompone automáticamente en sub-queries

**Tipos de queries multihop:**

#### a) **Condicionales** ("¿Puedo X si Y?")
```
✓ ¿Puedo ajustar el cronograma si estoy en fase II?
✓ Si mi proyecto es de salud, ¿qué OCAD lo evalúa?
✓ ¿Es posible modificar el presupuesto cuando el proyecto está aprobado?
```

**Cómo funciona:**
1. Sistema verifica la condición ("si estoy en fase II")
2. Busca la consecuencia ("¿puedo ajustar el cronograma?")
3. Combina ambas respuestas

#### b) **Comparativas** ("Diferencias entre A y B")
```
✓ Diferencias entre Acuerdo 03/2021 y Acuerdo 13/2025
✓ Compara requisitos de proyectos de CTEI vs infraestructura
✓ ¿Qué cambió entre la versión anterior y la actual?
```

**Cómo funciona:**
1. Busca información sobre A
2. Busca información sobre B
3. Sintetiza las diferencias

#### c) **Procedurales** ("Proceso de X")
```
✓ Proceso completo desde radicación hasta desembolso
✓ ¿Cómo solicitar un ajuste a un proyecto aprobado?
✓ Explica el procedimiento de viabilización paso a paso
```

**Cómo funciona:**
1. Identifica pasos del proceso
2. Busca cada paso por separado
3. Ensambla el procedimiento completo

#### d) **Agregación** ("Lista todos...")
```
✓ Lista todos los requisitos para proyectos de ciencia y tecnología
✓ Enumera las causales de liberación de recursos
✓ ¿Cuáles son todos los documentos necesarios?
```

**Cómo funciona:**
1. Búsqueda exhaustiva (top-K alto)
2. Recopila información fragmentada
3. Sintetiza lista completa

---

## 2️⃣ Mejores Prácticas

### ✅ SÍ - Menciona Secciones Específicas

**Para Documento Técnico V2**, usa números de sección:

```
✓ "sección 18 productos esperados"
✓ "sección 25 fuentes de financiación"
✓ "sección 6 antecedentes"
✓ "sección 14 metodología propuesta"
```

**Para Acuerdo Único 2025**, usa capítulos/artículos:

```
✓ "capítulo 4 ajustes de proyectos"
✓ "artículo 4.5.1.2 variables ajustables"
✓ "título 3 del acuerdo"
```

**¿Por qué funciona mejor?**
- El sistema detecta automáticamente el filtro de sección
- Reduce el espacio de búsqueda
- Aumenta la precisión (scores más altos)

---

### ✅ SÍ - Usa Terminología del Documento

**Documento Técnico V2:**

| ❌ No uses | ✅ Usa en su lugar |
|-----------|-------------------|
| "productos construidos" | "productos esperados" |
| "presupuesto" | "fuentes de financiación" |
| "resultados del proyecto" | "resultados e impactos esperados" |
| "antecedentes del proyecto" | "antecedentes" (sección 6) |

**Acuerdo Único 2025:**

| ❌ No uses | ✅ Usa en su lugar |
|-----------|-------------------|
| "aprobación de proyectos" | "viabilización de proyectos" |
| "modificaciones" | "ajustes a proyectos" |
| "comité" | "OCAD" |
| "cambios" | "ajustes" o "modificaciones" |

**¿Por qué funciona mejor?**
- El embedding vectorial coincide mejor con el contenido real
- Scores de relevancia más altos (>0.6 vs <0.3)

---

### ✅ SÍ - Sé Específico y Contextual

**Mal ❌:**
```
- "¿Qué requisitos hay?"
- "cuéntame del proyecto"
- "explica esto"
```

**Bien ✅:**
```
- "¿Qué requisitos hay para proyectos de CTEI en fase III?"
- "¿Cuáles son los productos esperados del proyecto en la sección 18?"
- "Explica el proceso de ajuste de proyectos aprobados según el capítulo 4"
```

**Regla de oro:** Tu query debe tener suficiente contexto para que alguien que no ha leído el documento entienda qué estás preguntando.

---

### ❌ NO - Queries Muy Genéricas

Estas queries suelen fallar:

```
❌ "cuéntame del documento"
❌ "qué dice aquí"
❌ "dame información"
❌ "resumen" (sin especificar qué resumir)
❌ "todo sobre X" (demasiado amplio)
```

**¿Por qué fallan?**
- Sin contexto específico, el embedding no puede determinar qué buscar
- Scores muy bajos (<0.2)
- Respuesta genérica o "No encontré información"

**Cómo mejorarlas:**
```
✓ "¿Qué dice la sección 18 sobre productos esperados?"
✓ "Resume el capítulo 4 sobre ajustes a proyectos"
✓ "Dame información sobre los requisitos de viabilización"
```

---

## 3️⃣ Ejemplos por Documento

### 📄 Documento Técnico V2

**Queries Probadas y Efectivas:**

#### Sobre Productos (Sección 18):
```
✅ "sección 18 productos esperados del proyecto"
✅ "¿cuáles son los entregables en la sección 18?"
✅ "lista los productos esperados según la sección 18"
```

#### Sobre Presupuesto/Financiación (Sección 25):
```
✅ "sección 25 resumen de fuentes de financiación"
✅ "¿cuál es el valor total del proyecto en la sección 25?"
✅ "fuentes de financiación y contrapartidas sección 25"
```

#### Sobre Metodología (Sección 14):
```
✅ "sección 14 metodología propuesta"
✅ "¿cuál es la metodología para desarrollar la alternativa seleccionada?"
✅ "describe la metodología en la sección 14"
```

#### Sobre Antecedentes (Sección 6):
```
✅ "sección 6 antecedentes del proyecto"
✅ "contexto histórico en la sección de antecedentes"
```

#### Queries Complejas (Multihop):
```
✅ "¿cuáles son los productos esperados y cuál es el valor total del proyecto?"
   → Sistema busca sección 18 + sección 25

✅ "compara la metodología de la sección 14 con los resultados esperados de la sección 17"
   → Sistema busca ambas secciones y compara
```

---

### 📄 Acuerdo Único 2025

**Queries Probadas y Efectivas:**

#### Sobre Ajustes (Capítulo 4):
```
✅ "capítulo 4 ajustes a proyectos aprobados"
✅ "¿qué variables puedo ajustar según el artículo 4.5.1.2?"
✅ "requisitos para ajustar un proyecto en el capítulo 4"
```

#### Sobre Viabilización:
```
✅ "proceso de viabilización de proyectos"
✅ "¿cómo se viabiliza un proyecto según el acuerdo?"
✅ "requisitos para la viabilización de proyectos de infraestructura"
```

#### Sobre OCAD:
```
✅ "¿qué es un OCAD según el acuerdo?"
✅ "funciones del OCAD"
✅ "tipos de OCAD y sus competencias"
```

#### Queries Complejas (Multihop):
```
✅ "¿puedo ajustar el cronograma de un proyecto en fase II?"
   → Sistema verifica: ¿cronograma es ajustable? + ¿requisitos fase II?

✅ "diferencias entre proyectos de CTEI y proyectos de infraestructura"
   → Sistema busca requisitos de ambos tipos y compara

✅ "proceso completo desde radicación hasta el primer desembolso"
   → Sistema identifica todos los pasos y los ensambla
```

---

## 4️⃣ Interpretando Resultados

### 🔍 Scores de Relevancia

El sistema asigna un score a cada chunk recuperado:

| Score | Interpretación | Acción Recomendada |
|-------|----------------|-------------------|
| **> 0.8** | Excelente coincidencia | ✅ Confía en la respuesta |
| **0.6 - 0.8** | Buena coincidencia | ✅ Respuesta confiable |
| **0.3 - 0.6** | Coincidencia moderada | ⚠️ Verifica citaciones |
| **< 0.3** | Baja coincidencia | ❌ Considera reformular |

**Si todos los scores son < 0.3:**
1. ✓ Menciona la sección/capítulo específico
2. ✓ Usa terminología exacta del documento
3. ✓ Sé más específico en tu pregunta
4. ✓ Revisa si el documento realmente contiene esa información

---

### 🚀 Indicadores Multihop

Cuando ves **"🚀 Multihop Retrieval"** en la interfaz:

**Significa que:**
- El sistema detectó que tu query es compleja
- Se ejecutaron múltiples búsquedas (sub-queries)
- Los chunks fueron fusionados inteligentemente

**En la lista de fuentes:**
- Chunks marcados con **🔗 N fuentes** fueron encontrados por múltiples sub-queries
- Estos chunks son más relevantes (boost factor aplicado)

**Boost Factor:**
- **1.0x**: Encontrado por 1 sub-query (relevancia normal)
- **1.3x**: Encontrado por 2 sub-queries (+30% relevancia)
- **1.5x**: Encontrado por 3+ sub-queries (+50% relevancia)

**Ejemplo:**
```
Si preguntas: "¿cuáles son los productos y cuál es el valor total?"

Sub-query 1: "productos esperados"  → encuentra chunk A (sección 18)
Sub-query 2: "valor total proyecto" → encuentra chunk B (sección 25)
                                    → también encuentra chunk A (financiación relacionada)

Chunk A encontrado por 2 sub-queries → Boost 1.3x → Aparece primero
Chunk B encontrado por 1 sub-query → Boost 1.0x → Aparece después
```

---

## 5️⃣ Tips Avanzados

### 💡 Para Queries Multihop (Complejas)

#### 1. **Condicionales ("¿Puedo X si Y?")**

**Cómo formular:**
```
✅ "¿Puedo ajustar el cronograma si estoy en fase II?"
✅ "Si mi proyecto es de salud con monto >5.000M, ¿qué OCAD lo evalúa?"
✅ "¿Es posible modificar el presupuesto cuando el proyecto está en ejecución?"
```

**El sistema:**
- Verificará automáticamente TODAS las condiciones
- Buscará las consecuencias para cada condición
- Sintetizará una respuesta que conecte ambas partes

---

#### 2. **Comparativas ("Diferencias entre A y B")**

**Cómo formular:**
```
✅ "Diferencias entre Acuerdo 03/2021 y Acuerdo 13/2025"
✅ "Compara requisitos de proyectos de CTEI vs infraestructura"
✅ "¿Qué cambió entre la sección 14 y la sección 17?"
```

**El sistema:**
- Buscará información de AMBOS lados de la comparación
- Asegurará que ambos lados estén representados en los chunks
- Sintetizará las diferencias de forma estructurada

---

#### 3. **Procedurales ("Proceso de X")**

**Cómo formular:**
```
✅ "Proceso completo desde radicación hasta desembolso"
✅ "¿Cómo solicitar un ajuste a un proyecto aprobado paso a paso?"
✅ "Explica el procedimiento de viabilización"
```

**El sistema:**
- Identificará múltiples pasos del proceso
- Buscará cada paso por separado
- Ensamblará el procedimiento completo en orden lógico

---

### ⚡ Para Mejor Performance

**Optimiza según el tipo de query:**

| Tipo de Query | Multihop | Razón |
|---------------|----------|-------|
| Simple definición | ❌ OFF | Más rápido (3-5s vs 8-15s) |
| Comparativa | ✅ ON | Necesita búsquedas múltiples |
| Condicional | ✅ ON | Requiere verificar condiciones |
| Procedural | ✅ ON | Pasos no adyacentes |
| Agregación | ⚠️ AUTO | Detecta automáticamente |

**Configuración recomendada:**
- 🔹 **Déjalo en ON (default)**: El sistema detecta automáticamente si la query es compleja
- 🔹 **Solo desactívalo** si sabes que TODAS tus queries son simples y quieres velocidad máxima

---

## 6️⃣ Casos de Uso Comunes

### Caso 1: "No encontré información"

**Problema:**
```
Query: "cuales son los productos que se construyen con este proyecto"
Respuesta: "No encontré información..."
```

**Solución:**
```
✅ "sección 18 productos esperados del proyecto"

Razón:
- Usa terminología exacta del documento ("productos esperados")
- Menciona sección específica (18)
- Score mejora de 0.02 → 0.65
```

---

### Caso 2: Scores muy bajos (<0.3)

**Problema:**
```
Query: "presupuesto del proyecto"
Score: 0.15 (muy bajo)
```

**Solución:**
```
✅ "sección 25 fuentes de financiación y valor total"

Razón:
- Documento usa "fuentes de financiación", no "presupuesto"
- Sección 25 específica
- Score mejora de 0.15 → 0.72
```

---

### Caso 3: Query multihop no descompone

**Problema:**
```
Query: "productos y valor"
Multihop: No se activó (query muy corta)
```

**Solución:**
```
✅ "¿cuáles son los productos esperados del proyecto y cuál es el valor total?"

Razón:
- Query más explícita
- Sistema detecta 2 preguntas distintas
- Multihop se activa automáticamente
```

---

## 7️⃣ Checklist de Query Efectiva

Antes de enviar tu query, verifica:

- [ ] ¿Mencioné la sección/capítulo específico si lo conozco?
- [ ] ¿Usé terminología del documento (no sinónimos genéricos)?
- [ ] ¿Mi query tiene suficiente contexto?
- [ ] ¿Es específica (no genérica como "cuéntame del documento")?
- [ ] Si es query multihop, ¿formulé claramente ambas partes?
- [ ] Si los scores son bajos, ¿probé reformular?

---

## 8️⃣ Ejemplos de Transformación

### Antes → Después

#### Ejemplo 1:
```
❌ "presupuesto"
✅ "sección 25 fuentes de financiación y valor total del proyecto"
```

#### Ejemplo 2:
```
❌ "productos construidos"
✅ "sección 18 productos esperados y entregables"
```

#### Ejemplo 3:
```
❌ "¿puedo cambiar algo?"
✅ "¿qué variables puedo ajustar según el capítulo 4 del acuerdo?"
```

#### Ejemplo 4:
```
❌ "diferencias entre documentos"
✅ "diferencias entre Acuerdo 03/2021 y Acuerdo 13/2025 en cuanto a ajustes de proyectos"
```

#### Ejemplo 5:
```
❌ "proceso"
✅ "proceso completo de viabilización desde radicación hasta aprobación"
```

---

## 9️⃣ FAQ

### P: ¿Cuándo debo activar Multihop?
**R:** Déjalo activado (default). Se activa automáticamente solo cuando detecta query compleja. No afecta queries simples.

### P: ¿Por qué mi query no encuentra nada aunque sé que está en el documento?
**R:** Tres razones comunes:
1. Terminología diferente (documento usa "X", tú preguntas por "Y")
2. Query muy genérica sin contexto
3. No mencionaste la sección específica

### P: ¿Cómo sé si mi query es multihop?
**R:** Si tu query tiene:
- "Si... entonces..."
- "Diferencias entre A y B"
- "Proceso completo de X"
- "¿Puedo X cuando Y?"
Probablemente es multihop.

### P: ¿Qué hago si los scores son todos <0.3?
**R:** Reformula usando:
1. Sección/capítulo específico
2. Terminología exacta del documento
3. Más contexto en la pregunta

### P: ¿Puedo hacer preguntas en inglés?
**R:** Los documentos están en español. Queries en inglés tendrán scores muy bajos. Usa español.

---

## 🎯 Resumen Ejecutivo

**Las 3 reglas de oro:**

1. **📍 Sé específico**: Menciona sección/capítulo si lo conoces
2. **📖 Usa terminología exacta**: Del documento, no sinónimos
3. **🎯 Da contexto**: Tu query debe ser auto-explicativa

**Ejemplos ganadores:**
```
✅ "sección 18 productos esperados"
✅ "capítulo 4 variables ajustables"
✅ "¿puedo ajustar el cronograma si estoy en fase II?"
```

**Ejemplos perdedores:**
```
❌ "productos"
❌ "qué dice aquí"
❌ "dame información"
```

---

**Fin de la Guía**

Para más información técnica, consulta:
- `docs/SISTEMA_MULTIHOP.md` - Documentación técnica del sistema multihop
- `docs/ARQUITECTURA_TECNICA.md` - Arquitectura completa del sistema
- `CHANGELOG.md` - Historial de cambios y versiones
