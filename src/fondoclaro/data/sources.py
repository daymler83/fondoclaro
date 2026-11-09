from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    format: str
    purpose: str


SP_CSV = "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php"
SP_RETURNS = "https://www.spensiones.cl/apps/rentabilidad/getRentabilidad.php?tiprent=FP"
BCCH_DAILY = "https://si3.bcentral.cl/indicadoressiete/secure/indicadoresdiarios.aspx?Idioma=es-CL"
SOURCES = (
    Source("sp_cuota", SP_CSV, "CSV ISO-8859-1, ;", "cuota y patrimonio diarios POR AFP; no es serie del sistema"),
    Source("sp_rentabilidad", SP_RETURNS, "HTML ISO-8859-1", "validación exclusivamente"),
    Source("bcch", BCCH_DAILY, "HTML UTF-8", "UF diaria; la captura actual no reemplaza el histórico"),
)
