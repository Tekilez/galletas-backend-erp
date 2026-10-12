-- =============================================================================
-- MIGRACION 009: Convertir catalogo ROPA -> GALLETAS (solo nombres, misma logica)
-- Fecha: 2026-10-12
-- Uso: ejecutar DESPUES de 002 en bases que ya tienen datos de ropa,
--      o junto a seed nuevo en el proyecto Galletar_Store.
-- No cambia tablas/columnas/endpoints. Solo renombra productos, categorias,
-- variantes (talla=presentacion, color=sabor) y SKUs.
-- Columnas talla/color conservan su nombre por compatibilidad con el backend.
-- =============================================================================

-- 1. Productos ropa -> galletas (por nombre exacto viejo)
UPDATE public.productos SET
  nombre = 'Galleta Chocochips Clasica',
  descripcion = 'Galleta con chispas de chocolate - Presentaciones PAQ6 a CAJA24',
  categoria = 'clasicas'
WHERE nombre = 'Pantalón Strech Semi Pitillo';

UPDATE public.productos SET
  nombre = 'Galleta Vainilla Francesa',
  descripcion = 'Galleta de vainilla estilo frances - Presentaciones PAQ6 a BOLSA1KG',
  categoria = 'clasicas'
WHERE nombre = 'Polo Camisero Cuello';

UPDATE public.productos SET
  nombre = 'Galleta Avena Integral',
  descripcion = 'Galleta de avena integral saludable',
  categoria = 'saludables'
WHERE nombre = 'Jeans Mom Fit';

UPDATE public.productos SET categoria = 'clasicas' WHERE categoria IN ('pantalones', 'polos');
UPDATE public.productos SET categoria = 'saludables' WHERE categoria IN ('jeans');

-- 2. Variantes: talla (numeros/letras ropa) -> presentaciones galleta
-- Mapeo conservador por grupos para no colisionar SKUs existentes:
-- 28, S      -> PAQ6
-- 29, M      -> PAQ12
-- 30, L      -> CAJA24
-- 32, XL     -> BOLSA500G
-- 34, 36+... -> BOLSA1KG / UNIDAD (reparto)
UPDATE public.variantes SET talla = 'PAQ6'      WHERE talla IN ('28', 'S');
UPDATE public.variantes SET talla = 'PAQ12'     WHERE talla IN ('29', 'M');
UPDATE public.variantes SET talla = 'CAJA24'    WHERE talla IN ('30', 'L');
UPDATE public.variantes SET talla = 'BOLSA500G' WHERE talla IN ('32', 'XL');
UPDATE public.variantes SET talla = 'BOLSA1KG'  WHERE talla IN ('34', '36', '38', '40', '42', '44', '2XL', '3XL', '4XL', 'XS');

-- 3. Variantes: color (ropa) -> sabor (galleta)
UPDATE public.variantes SET color = 'CHOCOCHIPS' WHERE color IN ('Negro', 'negro', 'NEGRO');
UPDATE public.variantes SET color = 'VAINILLA'   WHERE color IN ('Azul', 'azul', 'AZUL', 'Blanco', 'blanco', 'BLANCO');
UPDATE public.variantes SET color = 'AVENA'      WHERE color IN ('Celeste', 'celeste', 'CELESTE', 'Beige', 'beige', 'BEIGE');
UPDATE public.variantes SET color = 'MIXTO'      WHERE color IN ('Azul Oscuro', 'azul oscuro');

-- 4. SKUs ropa -> galletas (prefijos). Se hace por patrones para no romper FK.
-- PANT-* -> GALL-CHOCO-*, POLO-* -> GALL-VAIN-*, JEAN-* -> GALL-AVENA-*
UPDATE public.variantes SET sku = replace(sku, 'PANT-SP-NEG-', 'GALL-CHOCO-') WHERE sku LIKE 'PANT-SP-NEG-%';
UPDATE public.variantes SET sku = replace(sku, 'PANT-SP-AZU-', 'GALL-CHOCO-') WHERE sku LIKE 'PANT-SP-AZU-%';
UPDATE public.variantes SET sku = replace(sku, 'PANT-', 'GALL-CHOCO-') WHERE sku LIKE 'PANT-%';
UPDATE public.variantes SET sku = replace(sku, 'POLO-CC-NEG-', 'GALL-VAIN-') WHERE sku LIKE 'POLO-CC-NEG-%';
UPDATE public.variantes SET sku = replace(sku, 'POLO-', 'GALL-VAIN-') WHERE sku LIKE 'POLO-%';
UPDATE public.variantes SET sku = replace(sku, 'POL-', 'GALL-VAIN-') WHERE sku LIKE 'POL-%';
UPDATE public.variantes SET sku = replace(sku, 'JEAN-MOM-', 'GALL-AVENA-') WHERE sku LIKE 'JEAN-MOM-%';
UPDATE public.variantes SET sku = replace(sku, 'JEAN-', 'GALL-AVENA-') WHERE sku LIKE 'JEAN-%';
UPDATE public.variantes SET sku = replace(sku, 'JEA-', 'GALL-AVENA-') WHERE sku LIKE 'JEA-%';

-- Si algun SKU viejo numerico quedo con el numero de talla dentro (ej GALL-CHOCO-29),
-- se deja tal cual: sigue siendo unico y valido. El POS usa el id, no el texto.

-- 5. Motivos de kardex ropa -> galletas (solo texto)
UPDATE public.transacciones SET motivo = 'compra proveedor galletas' WHERE motivo = 'compra proveedor';

-- 6. Verificacion
-- SELECT p.nombre, p.categoria, v.sku, v.talla, v.color, v.stock_actual
-- FROM public.variantes v JOIN public.productos p ON p.id = v.producto_id
-- ORDER BY p.nombre, v.talla LIMIT 30;
