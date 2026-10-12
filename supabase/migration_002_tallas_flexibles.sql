-- =============================================================================
-- MIGRACION 002: Presentaciones flexibles para GALLETAS
-- Fecha: 2026-09-17 (adaptada a galletas, misma logica que version ropa)
-- talla = PRESENTACION (UNIDAD, PAQ6, PAQ12, CAJA24, BOLSA500G, BOLSA1KG...)
-- color = SABOR (CHOCOCHIPS, VAINILLA, AVENA, RELLENA, MANTEQUILLA, COCO...)
-- Solución: variantes.talla ya es varchar(20) flexible, pero se añade validación
--           explícita + normalización + datos de ejemplo.
-- Ejecutar en: Supabase Dashboard > SQL Editor > Run
-- =============================================================================

-- 1. Asegurar que talla siga siendo varchar(20) flexible (drop check restrictivo si existiera)
ALTER TABLE public.variantes DROP CONSTRAINT IF EXISTS chk_variantes_talla_enum;
ALTER TABLE public.variantes DROP CONSTRAINT IF EXISTS chk_talla_formato;

-- 2. Nuevo CHECK flexible: presentaciones de galletas
--    Acepta: UNIDAD, PAQ6, PAQ12, CAJA24, BOLSA500G, BOLSA1KG, DOCENA, GRANEL, PACK6, PACK12, UNICA
ALTER TABLE public.variantes
  ADD CONSTRAINT chk_talla_formato CHECK (
    talla ~* '^(UNIDAD|PAQ6|PAQ12|CAJA24|BOLSA500G|BOLSA1KG|DOCENA|GRANEL|PACK6|PACK12|UNICA|ÚNICA)$'
    AND length(talla) BETWEEN 1 AND 20
  );

-- 3. Normalización: trigger para trim + upper (misma logica, solo cambian ejemplos)
CREATE OR REPLACE FUNCTION public.normalizar_talla()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.talla := upper(btrim(NEW.talla));
  NEW.color := btrim(NEW.color);
  RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_variantes_normalizar_talla ON public.variantes;
CREATE TRIGGER trg_variantes_normalizar_talla
  BEFORE INSERT OR UPDATE OF talla, color ON public.variantes
  FOR EACH ROW EXECUTE FUNCTION public.normalizar_talla();

COMMENT ON COLUMN public.variantes.talla IS 'Presentación galleta: UNIDAD,PAQ6,PAQ12,CAJA24,BOLSA500G,BOLSA1KG,DOCENA,GRANEL. Caso principal = PAQ12 Chocochips.';
COMMENT ON COLUMN public.variantes.color IS 'Sabor galleta: CHOCOCHIPS,VAINILLA,AVENA,RELLENA,MANTEQUILLA,COCO,MIXTO.';

-- 4. Índice para búsqueda por presentación exacta - ya existe idx_variantes_talla_color pero reforzamos
CREATE INDEX IF NOT EXISTS idx_variantes_talla_exact ON public.variantes(talla);

-- 5. Vista helper: orden natural de presentaciones (UNIDAD < PAQ6 < PAQ12 < CAJA24 < granel)
CREATE OR REPLACE VIEW public.v_variantes_orden_talla AS
SELECT v.*,
  CASE
    WHEN upper(talla) = 'UNIDAD'    THEN 10
    WHEN upper(talla) = 'PAQ6'      THEN 20
    WHEN upper(talla) = 'PAQ12'     THEN 30
    WHEN upper(talla) = 'PACK6'     THEN 31
    WHEN upper(talla) = 'PACK12'    THEN 32
    WHEN upper(talla) = 'DOCENA'    THEN 33
    WHEN upper(talla) = 'CAJA24'    THEN 40
    WHEN upper(talla) = 'BOLSA500G' THEN 50
    WHEN upper(talla) = 'BOLSA1KG'  THEN 60
    WHEN upper(talla) = 'GRANEL'    THEN 70
    ELSE 200
  END AS talla_orden
FROM public.variantes v;

-- 6. Datos de ejemplo GALLETAS (misma estructura que version ropa)
--    Producto 1: Galleta Chocochips Clasica (PAQ6, PAQ12, CAJA24, BOLSA500G, BOLSA1KG)
--    Producto 2: Galleta Vainilla Francesa (PAQ6, PAQ12, CAJA24...)
DO $$
DECLARE
  pid_choco uuid;
  pid_vain uuid;
BEGIN
  -- Chocochips (si no existe lo crea)
  INSERT INTO public.productos (nombre, descripcion, categoria, margen_ganancia)
  VALUES ('Galleta Chocochips Clasica', 'Galleta con chispas de chocolate. Presentaciones PAQ6-CAJA24', 'clasicas', 45.00)
  ON CONFLICT DO NOTHING
  RETURNING id INTO pid_choco;

  SELECT id INTO pid_choco FROM public.productos WHERE nombre='Galleta Chocochips Clasica' LIMIT 1;

  INSERT INTO public.productos (nombre, descripcion, categoria, margen_ganancia)
  VALUES ('Galleta Vainilla Francesa', 'Galleta de vainilla estilo frances. Presentaciones PAQ6-BOLSA1KG', 'clasicas', 40.00)
  ON CONFLICT DO NOTHING;

  SELECT id INTO pid_vain FROM public.productos WHERE nombre='Galleta Vainilla Francesa' LIMIT 1;

  -- Variantes chocochips: cada presentación es SKU distinto.
  -- Usa ON CONFLICT (sku) DO NOTHING para idempotencia
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_choco, 'GALL-CHOCO-PAQ6',   'PAQ6',      'CHOCOCHIPS', 8, 2, 8.50, 12.50),
    (pid_choco, 'GALL-CHOCO-PAQ12',  'PAQ12',     'CHOCOCHIPS', 5, 2, 15.00, 21.75),
    (pid_choco, 'GALL-CHOCO-CAJA24', 'CAJA24',    'CHOCOCHIPS', 6, 2, 28.00, 40.60),
    (pid_choco, 'GALL-CHOCO-500G',   'BOLSA500G', 'CHOCOCHIPS', 10, 2, 12.00, 17.40),
    (pid_choco, 'GALL-CHOCO-1KG',    'BOLSA1KG',  'CHOCOCHIPS', 4, 2, 22.00, 31.90),
    (pid_choco, 'GALL-CHOCO-PAQ6-VAIN', 'PAQ6',   'VAINILLA', 5, 2, 8.00, 11.50),
    (pid_choco, 'GALL-CHOCO-PAQ12-VAIN', 'PAQ12', 'VAINILLA', 7, 2, 15.00, 21.00),
    (pid_choco, 'GALL-CHOCO-CAJA24-VAIN', 'CAJA24', 'VAINILLA', 6, 2, 28.00, 39.50),
    (pid_choco, 'GALL-CHOCO-500G-AVENA', 'BOLSA500G', 'AVENA', 3, 2, 12.50, 18.00),
    (pid_choco, 'GALL-CHOCO-UNIDAD', 'UNIDAD',    'CHOCOCHIPS', 25, 5, 1.50, 2.50)
  ON CONFLICT (sku) DO NOTHING;

  -- Variantes vainilla: PAQ6, PAQ12, CAJA24, BOLSA500G, BOLSA1KG
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_vain, 'GALL-VAIN-PAQ6',   'PAQ6',      'VAINILLA', 12, 3, 7.50, 10.50),
    (pid_vain, 'GALL-VAIN-PAQ12',  'PAQ12',     'VAINILLA', 15, 3, 14.00, 19.60),
    (pid_vain, 'GALL-VAIN-CAJA24', 'CAJA24',    'VAINILLA', 10, 3, 26.00, 36.40),
    (pid_vain, 'GALL-VAIN-500G',   'BOLSA500G', 'VAINILLA', 8, 3, 11.00, 15.40),
    (pid_vain, 'GALL-VAIN-1KG',    'BOLSA1KG',  'VAINILLA', 5, 3, 20.00, 28.00)
  ON CONFLICT (sku) DO NOTHING;

  RAISE NOTICE 'Migración 002 OK galletas: Chocochips % Vainilla %', pid_choco, pid_vain;
END $$;

-- 7. Test rápido de validación (descomentar para probar)
-- SELECT * FROM public.v_variantes_orden_talla ORDER BY talla_orden LIMIT 20;
-- INSERT INTO public.variantes (producto_id, sku, talla, color, precio_costo, precio_venta) VALUES ((SELECT id FROM productos LIMIT 1), 'TEST-PAQ12', 'PAQ12', 'CHOCOCHIPS', 10, 15); -- debe OK
-- INSERT INTO public.variantes (producto_id, sku, talla, color, precio_costo, precio_venta) VALUES ((SELECT id FROM productos LIMIT 1), 'TEST-MALA', 'XXXXL', 'CHOCOCHIPS', 10, 15); -- debe fallar CHECK
