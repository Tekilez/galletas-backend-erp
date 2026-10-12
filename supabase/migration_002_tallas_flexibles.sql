-- =============================================================================
-- MIGRACION 002: Tallas flexibles (numéricas 28-44 para pantalones + letras S/M/L/XL)
-- Fecha: 2026-09-17
-- Problema: El cuaderno usa pantalones talla 29, 28, 30...44 y polos S/M/L/XL/2XL
-- Si solo se usa "M" para todo, el vendedor no puede encontrar talla 29.
-- Solución: variantes.talla ya es varchar(20) flexible, pero se añade validación
--           explícita + normalización + datos de ejemplo.
-- Ejecutar en: Supabase Dashboard > SQL Editor > Run
-- =============================================================================

-- 1. Asegurar que talla siga siendo varchar(20) flexible (drop check restrictivo si existiera)
ALTER TABLE public.variantes DROP CONSTRAINT IF EXISTS chk_variantes_talla_enum;
ALTER TABLE public.variantes DROP CONSTRAINT IF EXISTS chk_talla_formato;

-- 2. Nuevo CHECK flexible: permite letras estándar Y números 24-50 (pantalones/jeans)
--    Acepta: XS,S,M,L,XL,2XL,3XL,4XL, UNICA, ÚNICA, y números 24-50
ALTER TABLE public.variantes
  ADD CONSTRAINT chk_talla_formato CHECK (
    talla ~* '^(XXS|XS|S|M|L|XL|2XL|3XL|4XL|UNICA|ÚNICA|[0-9]{2,3})$'
    AND length(talla) BETWEEN 1 AND 20
  );

-- 3. Normalización: trigger para trim + upper en letras, deja número tal cual
CREATE OR REPLACE FUNCTION public.normalizar_talla()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.talla := btrim(NEW.talla);
  -- Si es puramente numérica, deja como está (ej "29", "32")
  IF NEW.talla ~ '^[0-9]+$' THEN
    -- valida rango pantalón peruano 24-50
    IF (NEW.talla::int < 24 OR NEW.talla::int > 50) THEN
      RAISE EXCEPTION 'Talla numérica fuera de rango (24-50): %', NEW.talla;
    END IF;
  ELSE
    -- Letras -> mayúsculas (m -> M, xl -> XL)
    NEW.talla := upper(NEW.talla);
  END IF;
  NEW.color := btrim(NEW.color);
  RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_variantes_normalizar_talla ON public.variantes;
CREATE TRIGGER trg_variantes_normalizar_talla
  BEFORE INSERT OR UPDATE OF talla, color ON public.variantes
  FOR EACH ROW EXECUTE FUNCTION public.normalizar_talla();

COMMENT ON COLUMN public.variantes.talla IS 'Talla flexible: S,M,L,XL,2XL,3XL para polos/casacas Y 28,29,30...44 para pantalones/jeans. Caso 29 = pantalón strech cintura 29.';

-- 4. Índice para búsqueda por talla exacta (numérica o letra) - ya existe idx_variantes_talla_color pero reforzamos
CREATE INDEX IF NOT EXISTS idx_variantes_talla_exact ON public.variantes(talla);
CREATE INDEX IF NOT EXISTS idx_variantes_talla_num ON public.variantes((talla::int)) WHERE talla ~ '^[0-9]+$';

-- 5. Vista helper: orden natural de tallas (numéricas primero 28-44, luego letras)
CREATE OR REPLACE VIEW public.v_variantes_orden_talla AS
SELECT v.*,
  CASE
    WHEN talla ~ '^[0-9]+$' THEN talla::int
    WHEN upper(talla) = 'XS'  THEN 100
    WHEN upper(talla) = 'S'   THEN 101
    WHEN upper(talla) = 'M'   THEN 102
    WHEN upper(talla) = 'L'   THEN 103
    WHEN upper(talla) = 'XL'  THEN 104
    WHEN upper(talla) = '2XL' THEN 105
    WHEN upper(talla) = '3XL' THEN 106
    ELSE 200
  END AS talla_orden
FROM public.variantes v;

-- 6. Datos de ejemplo REALES según cuaderno WhatsApp 2026-09-13
--    Producto 1: Pantalón Strech Semi Pitillo Sin Rasgar (tallas 28-44)
--    Producto 2: Polo Camisero / Polo Cuello (tallas S-2XL)
DO $$
DECLARE
  pid_pantalon uuid;
  pid_polo uuid;
BEGIN
  -- Pantalón (si no existe lo crea)
  INSERT INTO public.productos (nombre, descripcion, categoria, margen_ganancia)
  VALUES ('Pantalón Strech Semi Pitillo', 'Pantalón strech semi pitillo - Sin rasgar / Azul 2coro, choco, negro. Tallas 28-44', 'pantalones', 45.00)
  ON CONFLICT DO NOTHING
  RETURNING id INTO pid_pantalon;

  SELECT id INTO pid_pantalon FROM public.productos WHERE nombre='Pantalón Strech Semi Pitillo' LIMIT 1;

  INSERT INTO public.productos (nombre, descripcion, categoria, margen_ganancia)
  VALUES ('Polo Camisero Cuello', 'Polo camisero cuello - Rif Five / Negro. Tallas S-2XL. También Polo Stosh semi pitillo 28-36', 'polos', 40.00)
  ON CONFLICT DO NOTHING;

  SELECT id INTO pid_polo FROM public.productos WHERE nombre='Polo Camisero Cuello' LIMIT 1;

  -- Variantes pantalón: tallas 28-44 por 2 colores ejemplo (Negro, Azul). Cada talla es SKU distinto.
  -- Usa ON CONFLICT (sku) DO NOTHING para idempotencia
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_pantalon, 'PANT-SP-NEG-28', '28', 'Negro', 5, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-29', '29', 'Negro', 5, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-30', '30', 'Negro', 8, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-32', '32', 'Negro', 10, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-34', '34', 'Negro', 6, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-36', '36', 'Negro', 4, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-38', '38', 'Negro', 3, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-40', '40', 'Negro', 2, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-42', '42', 'Negro', 2, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-44', '44', 'Negro', 1, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-AZU-28', '28', 'Azul', 5, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-AZU-29', '29', 'Azul', 5, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-AZU-30', '30', 'Azul', 8, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-AZU-32', '32', 'Azul', 10, 2, 55.00, 79.75)
  ON CONFLICT (sku) DO NOTHING;

  -- Variantes polo: S, M, L, XL, 2XL por color Negro
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_polo, 'POLO-CC-NEG-S',   'S',   'Negro', 12, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-M',   'M',   'Negro', 15, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-L',   'L',   'Negro', 10, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-XL',  'XL',  'Negro', 8, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-2XL', '2XL', 'Negro', 5, 3, 28.00, 39.20)
  ON CONFLICT (sku) DO NOTHING;

  RAISE NOTICE 'Migración 002 OK: Pantalón % Polo %', pid_pantalon, pid_polo;
END $$;

-- 7. Test rápido de validación (descomentar para probar)
-- SELECT * FROM public.v_variantes_orden_talla ORDER BY talla_orden LIMIT 20;
-- INSERT INTO public.variantes (producto_id, sku, talla, color, precio_costo, precio_venta) VALUES ((SELECT id FROM productos LIMIT 1), 'TEST-29', '29', 'Rojo', 10, 15); -- debe OK
-- INSERT INTO public.variantes (producto_id, sku, talla, color, precio_costo, precio_venta) VALUES ((SELECT id FROM productos LIMIT 1), 'TEST-MALA', 'XXXXL', 'Rojo', 10, 15); -- debe fallar CHECK
