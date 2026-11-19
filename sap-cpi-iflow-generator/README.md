# sap-cpi-iflow-generator (skill)

Skill para que un modelo (Opus 5.5 o superior) genere, modifique y revise iFlows de SAP Cloud Integration como
código (`.iflw` + zip importable) **sin rellenar huecos con suposiciones**: todo sale del catálogo real del tenant
y de reglas comprobadas subiendo iFlows al tenant de pruebas de Avvale (16/11/2026).

## Qué contiene

| Ruta | Para qué |
|---|---|
| `SKILL.md` | Punto de entrada para el modelo: reglas de oro y flujo de trabajo |
| `catalog/components.json` | 150 componentes (pasos, eventos, procesos y adaptadores SAP) con claves, valores por defecto, valores permitidos, obligatoriedad condicional, regex y versión vigente en el tenant |
| `reference/*.md` | Anatomía del .iflw, reglas de serialización, reglas de legalidad (lo que el tenant rechaza o acepta en silencio), adaptadores, bucle de validación contra el tenant y registro de experimentos |
| `scripts/iflowgen.py` | Spec JSON → `.iflw` completo (identidades, todas las propiedades, diagrama) |
| `scripts/validate_iflw.py` | Validador estático (FATAL/ERROR/WARN) calibrado contra el tenant |
| `scripts/package_iflow.py` | `.iflw` + recursos → zip importable (MANIFEST, .project, metainfo, parameters) |
| `scripts/build_catalog.py`, `scripts/harvest/*` | Refrescar el catálogo desde otro tenant o tras una actualización de SAP |
| `examples/good/*.json` | Specs que generan iFlows con 0 problemas en el tenant (uno de ellos desplegado y arrancado) |

## Uso rápido

```bash
python scripts/iflowgen.py examples/good/deployable-router-localprocess.json -o "Mi Flujo.iflw"
python scripts/validate_iflw.py "Mi Flujo.iflw" --resources recursos
python scripts/package_iflow.py --iflw "Mi Flujo.iflw" --id avvale.mi.flujo --name "Mi Flujo" --resources recursos --out mi_flujo.zip
python scripts/validate_iflw.py mi_flujo.zip
```
Después: Add > Integration Flow > Upload en el paquete, y comprobar `validationResultModel` (ver
`reference/tenant-validation.md`).

## Instalación como skill

Copiar la carpeta a `~/.claude/skills/sap-cpi-iflow-generator/` (Claude Code) o empaquetarla como skill de
organización. Requiere Python 3.11+ (sin dependencias externas).
