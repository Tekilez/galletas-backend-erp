-- =============================================================================
-- SEED DATOS - Kardex Ropa (ejecutar despues de schema.sql y migration_002)
-- Supabase Dashboard > SQL Editor > Run
-- Incluye: Pantalon 29 (caso critico), Polo M/XL, transacciones de entrada
-- =============================================================================

-- 1. PRODUCTOS
INSERT INTO public.productos (id, nombre, descripcion, categoria, margen_ganancia) VALUES
  (gen_random_uuid(), 'Pantalón Strech Semi Pitillo', 'Pantalón strech semi pitillo sin rasgar - Tallas 28 a 44', 'pantalones', 45.00),
  (gen_random_uuid(), 'Polo Camisero Cuello', 'Polo camisero cuello Rif Five - Tallas S a 2XL', 'polos', 40.00),
  (gen_random_uuid(), 'Jeans Mom Fit', 'Jeans mom fit tiro alto', 'jeans', 50.00)
ON CONFLICT DO NOTHING;

-- Ver ids generados (copia ids para variantes si necesitas)
-- SELECT id, nombre FROM public.productos;

-- 2. VARIANTES (SKU vendible) - talla flexible: 29 numerica + M letra
-- Usa subselect por nombre para no hardcodear UUID
DO $$
DECLARE
  pid_pantalon uuid;
  pid_polo uuid;
  pid_jeans uuid;
BEGIN
  SELECT id INTO pid_pantalon FROM public.productos WHERE nombre='Pantalón Strech Semi Pitillo' LIMIT 1;
  SELECT id INTO pid_polo     FROM public.productos WHERE nombre='Polo Camisero Cuello' LIMIT 1;
  SELECT id INTO pid_jeans    FROM public.productos WHERE nombre='Jeans Mom Fit' LIMIT 1;

  -- Pantalon: tallas 28,29,30,32 (29 es el caso raro que antes era solo M)
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_pantalon, 'PANT-SP-NEG-28', '28', 'Negro', 8, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-29', '29', 'Negro', 5, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-30', '30', 'Negro', 6, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-NEG-32', '32', 'Negro', 10, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-AZU-29', '29', 'Azul', 4, 2, 55.00, 79.75),
    (pid_pantalon, 'PANT-SP-AZU-32', '32', 'Azul', 7, 2, 55.00, 79.75)
  ON CONFLICT (sku) DO NOTHING;

  -- Polo: tallas S/M/L/XL/2XL
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_polo, 'POLO-CC-NEG-S',   'S',   'Negro', 12, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-M',   'M',   'Negro', 15, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-L',   'L',   'Negro', 10, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-XL',  'XL',  'Negro', 8, 3, 28.00, 39.20),
    (pid_polo, 'POLO-CC-NEG-2XL', '2XL', 'Negro', 5, 3, 28.00, 39.20)
  ON CONFLICT (sku) DO NOTHING;

  -- Jeans: talla 32 numerica
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_jeans, 'JEAN-MOM-32-CEL', '32', 'Celeste', 20, 5, 58.00, 87.00)
  ON CONFLICT (sku) DO NOTHING;
END $$;

-- 3. TRANSACCIONES (KARDEX) - ejemplo: compra proveedor entrada para talla 29
-- IMPORTANTE: stock_anterior debe ser el stock_actual actual, stock_nuevo = anterior + cantidad (para entrada)
-- El trigger aplicar_transaccion_kardex actualiza variantes.stock_actual automaticamente
DO $$
DECLARE
  v_id uuid;
  v_stock int;
BEGIN
  SELECT id, stock_actual INTO v_id, v_stock FROM public.variantes WHERE sku='PANT-SP-NEG-29' LIMIT 1;
  IF v_id IS NOT NULL THEN
    INSERT INTO public.transacciones (variante_id, tipo, cantidad, precio_unitario, stock_anterior, stock_nuevo, motivo, referencia)
    VALUES (v_id, 'entrada', 6, 55.00, v_stock, v_stock + 6, 'compra proveedor', 'BOLETA F001-001')
    ON CONFLICT DO NOTHING;
  END IF;

  SELECT id, stock_actual INTO v_id, v_stock FROM public.variantes WHERE sku='POLO-CC-NEG-M' LIMIT 1;
  IF v_id IS NOT NULL THEN
    INSERT INTO public.transacciones (variante_id, tipo, cantidad, precio_unitario, stock_anterior, stock_nuevo, motivo, referencia)
    VALUES (v_id, 'salida', 2, 39.20, v_stock, v_stock - 2, 'venta POS', 'TICKET POS-001')
    ON CONFLICT DO NOTHING;
  END IF;
END $$;

-- 4. VERIFICACION
SELECT p.nombre, v.sku, v.talla, v.color, v.stock_actual FROM public.variantes v JOIN public.productos p ON p.id=v.producto_id ORDER BY p.nombre, v.talla;
SELECT * FROM public.v_kardex_detalle ORDER BY created_at DESC LIMIT 10;
